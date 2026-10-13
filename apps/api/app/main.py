from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models as m, schemas as s
from .db import database, tenant_context
from .security import (ACADEMIC_WRITERS, DUMMY_HASH, MANAGERS, PEOPLE_WRITERS, bearer,
                       current_user, hash_token, membership, password_hasher, permit,
                       require_platform, verify_password)

app = FastAPI(title="Siesco · Portal Escolar", version="0.1.0", description="API de demonstração. Dados sintéticos; revisão de segurança obrigatória antes de produção.")
PREFIX = "/api/v1"
TENANT = PREFIX + "/institutions/{institution_id}"


@app.middleware("http")
async def request_metadata(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def error_response(request, status, message, fields=None):
    return JSONResponse(status_code=status, content={"error": {"code": str(status), "message": message,
                        "request_id": request.state.request_id, "fields": fields or []}})


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error_response(request, exc.status_code, exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return error_response(request, 422, "Revise os campos informados.",
                          [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()])


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return error_response(request, 409, "Registro duplicado ou vínculo incompatível. Revise os dados.")


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    import logging
    logging.getLogger("portal").error("request_id=%s exception_type=%s", request.state.request_id, type(exc).__name__)
    return error_response(request, 500, "Não foi possível concluir a operação. Tente novamente.")


@app.get("/health", tags=["Operação"])
def health(db: Session = Depends(database, scope="function")):
    db.execute(select(1))
    return {"status": "ok"}


@app.post(PREFIX + "/auth/login", response_model=s.TokenOut, tags=["Autenticação"])
def login(payload: s.Login, db: Session = Depends(database, scope="function")):
    email = str(payload.email).lower()
    key = hash_token(email)
    recent = datetime.now(timezone.utc) - timedelta(minutes=10)
    attempts = db.scalar(select(func.count()).select_from(m.LoginAttempt).where(m.LoginAttempt.key == key, m.LoginAttempt.occurred_at > recent))
    if attempts >= 10:
        raise HTTPException(429, "Muitas tentativas. Aguarde 10 minutos.")
    db.execute(delete(m.LoginAttempt).where(m.LoginAttempt.occurred_at < recent))
    user = db.scalar(select(m.User).where(m.User.email == email))
    valid = verify_password(user.password_hash if user else DUMMY_HASH, payload.password)
    if not valid or not user or not user.active:
        db.add(m.LoginAttempt(key=key))
        db.commit()  # Persistir a tentativa mesmo com a resposta 401.
        raise HTTPException(401, "E-mail ou senha inválidos.")
    token = token_urlsafe(48)
    db.add(m.LoginSession(token_hash=hash_token(token), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=8)))
    return {"access_token": token, "token_type": "bearer", "expires_in": 28800}


@app.post(PREFIX + "/auth/logout", status_code=204, tags=["Autenticação"])
def logout(user=Depends(current_user), credentials=Depends(bearer), db: Session = Depends(database, scope="function")):
    db.execute(delete(m.LoginSession).where(m.LoginSession.token_hash == hash_token(credentials.credentials)))


@app.get(PREFIX + "/me", response_model=s.MeOut, tags=["Autenticação"])
def me(user=Depends(current_user), db: Session = Depends(database, scope="function")):
    rows = db.execute(select(m.Membership, m.Institution).join(m.Institution, m.Institution.id == m.Membership.institution_id).where(m.Membership.user_id == user.id)).all()
    return {"id": user.id, "name": user.name, "email": user.email, "platform_admin": user.platform_admin,
            "memberships": [{"institution_id": i.id, "institution_name": i.name, "school_id": member.school_id, "role": member.role} for member, i in rows]}


@app.get(PREFIX + "/platform/institutions", response_model=list[s.InstitutionOut], tags=["Plataforma"])
def institutions(user=Depends(require_platform), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    return db.scalars(select(m.Institution).order_by(m.Institution.name, m.Institution.id).offset(offset).limit(limit)).all()


@app.post(PREFIX + "/platform/institutions", response_model=s.InstitutionOut, status_code=201, tags=["Plataforma"])
def create_institution(payload: s.InstitutionIn, user=Depends(require_platform), db: Session = Depends(database, scope="function")):
    institution = m.Institution(name=payload.name, slug=payload.slug)
    db.add(institution)
    db.flush()
    tenant_context(db, institution.id)
    school = m.School(institution_id=institution.id, name="Unidade principal")
    director = m.User(name=payload.director_name, email=str(payload.director_email).lower(), password_hash=password_hasher.hash(payload.director_password))
    db.add_all([school, director])
    db.flush()
    db.add(m.Membership(user_id=director.id, institution_id=institution.id, school_id=school.id, role="director"))
    db.add(m.AuditEvent(institution_id=institution.id, school_id=school.id, actor_id=user.id, action="institutions.create", entity_id=institution.id))
    db.flush()
    return institution


def scoped(model, member):
    return select(model).where(model.institution_id == member.institution_id, model.school_id == member.school_id)


def find(db, model, item_id, member, lock=False):
    statement = scoped(model, member).where(model.id == str(item_id))
    item = db.scalar(statement.with_for_update() if lock else statement)
    if not item:
        raise HTTPException(404, "Registro não encontrado.")
    return item


def audit(db, member, action, item_id):
    db.add(m.AuditEvent(institution_id=member.institution_id, school_id=member.school_id,
                       actor_id=member.user_id, action=action, entity_id=item_id))


def create(db, model, values, member):
    item = model(**values, institution_id=member.institution_id, school_id=member.school_id)
    db.add(item)
    db.flush()
    audit(db, member, model.__tablename__ + ".create", item.id)
    db.flush()
    return item


def register_catalog(path, model, schema, output, writers):
    def list_items(member=Depends(membership), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), q: str = Query("", max_length=100)):
        permit(member, MANAGERS)
        stmt = scoped(model, member)
        if q:
            stmt = stmt.where(model.name.icontains(q, autoescape=True))
        return db.scalars(stmt.order_by(model.name, model.id).offset(offset).limit(limit)).all()

    def create_item(payload: schema, member=Depends(membership), db: Session = Depends(database, scope="function")):
        permit(member, writers)
        values = payload.model_dump(mode="json")
        if "email" in values:
            values["email"] = values["email"].lower()
        if "birth_date" in values:
            values["birth_date"] = payload.birth_date
        return create(db, model, values, member)

    def update_item(item_id: UUID, payload: schema, member=Depends(membership), db: Session = Depends(database, scope="function")):
        permit(member, writers)
        item = find(db, model, item_id, member, lock=True)
        if model is m.ClassGroup:
            count = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.class_id == item.id))
            if count and (item.academic_year != payload.academic_year or item.grade_level != payload.grade_level):
                raise HTTPException(409, "Ano e etapa de uma turma com matrículas não podem ser alterados.")
            occupied = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.class_id == item.id, m.Enrollment.status == "active"))
            if payload.capacity < occupied:
                raise HTTPException(409, "Capacidade menor que o número de matrículas ativas.")
        for key, value in payload.model_dump().items():
            setattr(item, key, value.lower() if key == "email" else value)
        audit(db, member, path + ".update", item.id)
        db.flush()
        return item

    app.add_api_route(TENANT + "/" + path, list_items, methods=["GET"], response_model=list[output], tags=[path], name="list_" + path)
    app.add_api_route(TENANT + "/" + path, create_item, methods=["POST"], response_model=output, status_code=201, tags=[path], name="create_" + path)
    app.add_api_route(TENANT + "/" + path + "/{item_id}", update_item, methods=["PUT"], response_model=output, tags=[path], name="update_" + path)


for args in [("students", m.Student, s.StudentIn, s.StudentOut, PEOPLE_WRITERS),
             ("guardians", m.Guardian, s.GuardianIn, s.GuardianOut, PEOPLE_WRITERS),
             ("teachers", m.Teacher, s.TeacherIn, s.TeacherOut, ACADEMIC_WRITERS),
             ("subjects", m.Subject, s.SubjectIn, s.SubjectOut, ACADEMIC_WRITERS),
             ("classes", m.ClassGroup, s.ClassIn, s.ClassOut, ACADEMIC_WRITERS)]:
    register_catalog(*args)


@app.get(TENANT + "/guardian-links", response_model=list[s.LinkOut], tags=["Vínculos"])
def links(member=Depends(membership), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    permit(member, MANAGERS)
    return db.scalars(scoped(m.GuardianLink, member).order_by(m.GuardianLink.id).offset(offset).limit(limit)).all()


@app.post(TENANT + "/guardian-links", response_model=s.LinkOut, status_code=201, tags=["Vínculos"])
def create_link(payload: s.LinkIn, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, PEOPLE_WRITERS)
    find(db, m.Student, payload.student_id, member)
    find(db, m.Guardian, payload.guardian_id, member)
    return create(db, m.GuardianLink, payload.model_dump(mode="json"), member)


@app.delete(TENANT + "/guardian-links/{item_id}", status_code=204, tags=["Vínculos"])
def revoke_link(item_id: UUID, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, PEOPLE_WRITERS)
    item = find(db, m.GuardianLink, item_id, member)
    item.verified = False
    audit(db, member, "guardian_links.revoke", item.id)


@app.put(TENANT + "/guardian-links/{item_id}", response_model=s.LinkOut, tags=["Vínculos"])
def update_link(item_id: UUID, payload: s.LinkIn, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, PEOPLE_WRITERS)
    item = find(db, m.GuardianLink, item_id, member, lock=True)
    find(db, m.Student, payload.student_id, member)
    find(db, m.Guardian, payload.guardian_id, member)
    for key, value in payload.model_dump(mode="json").items():
        setattr(item, key, value)
    audit(db, member, "guardian_links.update", item.id)
    db.flush()
    return item


@app.get(TENANT + "/assignments", response_model=list[s.AssignmentOut], tags=["Atribuições"])
def assignments(member=Depends(membership), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    permit(member, MANAGERS)
    return db.scalars(scoped(m.Assignment, member).order_by(m.Assignment.id).offset(offset).limit(limit)).all()


@app.post(TENANT + "/assignments", response_model=s.AssignmentOut, status_code=201, tags=["Atribuições"])
def create_assignment(payload: s.AssignmentIn, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, ACADEMIC_WRITERS)
    for model, identifier in [(m.ClassGroup, payload.class_id), (m.Subject, payload.subject_id), (m.Teacher, payload.teacher_id)]:
        find(db, model, identifier, member)
    return create(db, m.Assignment, payload.model_dump(mode="json"), member)


@app.get(TENANT + "/enrollments", response_model=list[s.EnrollmentOut], tags=["Matrículas"])
def enrollments(member=Depends(membership), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    permit(member, MANAGERS)
    return db.scalars(scoped(m.Enrollment, member).order_by(m.Enrollment.id).offset(offset).limit(limit)).all()


@app.post(TENANT + "/enrollments", response_model=s.EnrollmentOut, status_code=201, tags=["Matrículas"])
def create_enrollment(payload: s.EnrollmentIn, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, PEOPLE_WRITERS)
    find(db, m.Student, payload.student_id, member)
    group = find(db, m.ClassGroup, payload.class_id, member, lock=True)
    occupied = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.class_id == group.id, m.Enrollment.status == "active"))
    if occupied >= group.capacity:
        raise HTTPException(409, "A turma está sem vagas.")
    existing = db.scalar(scoped(m.Enrollment, member).where(m.Enrollment.student_id == str(payload.student_id), m.Enrollment.academic_year == group.academic_year))
    if existing:
        raise HTTPException(409, "O aluno já possui matrícula neste ano letivo.")
    return create(db, m.Enrollment, {**payload.model_dump(mode="json"), "academic_year": group.academic_year}, member)


@app.post(TENANT + "/enrollments/{item_id}/cancel", response_model=s.EnrollmentOut, tags=["Matrículas"])
def cancel_enrollment(item_id: UUID, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, PEOPLE_WRITERS)
    item = find(db, m.Enrollment, item_id, member)
    find(db, m.ClassGroup, item.class_id, member, lock=True)
    item.status = "cancelled"
    audit(db, member, "enrollments.cancel", item.id)
    return item


@app.get(TENANT + "/dashboard", response_model=s.DashboardOut, tags=["Dashboard"])
def dashboard(member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, MANAGERS)
    counts = {name: db.scalar(select(func.count()).select_from(model).where(model.institution_id == member.institution_id, model.school_id == member.school_id))
              for name, model in [("students", m.Student), ("guardians", m.Guardian), ("teachers", m.Teacher), ("subjects", m.Subject), ("classes", m.ClassGroup)]}
    counts["enrollments"] = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.institution_id == member.institution_id, m.Enrollment.school_id == member.school_id, m.Enrollment.status == "active"))
    groups = db.execute(select(m.ClassGroup.name, m.ClassGroup.capacity, func.count(m.Enrollment.id)).outerjoin(m.Enrollment, (m.Enrollment.class_id == m.ClassGroup.id) & (m.Enrollment.status == "active")).where(m.ClassGroup.institution_id == member.institution_id, m.ClassGroup.school_id == member.school_id).group_by(m.ClassGroup.id).order_by(m.ClassGroup.name).limit(6)).all()
    return {"counts": counts, "occupancy": [{"name": name, "capacity": capacity, "enrolled": enrolled} for name, capacity, enrolled in groups]}


@app.get(TENANT + "/portal", response_model=s.PortalOut, tags=["Portal por vínculo"])
def portal(member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, {"teacher", "student", "guardian"})
    students = scoped(m.Student, member)
    if member.role == "student":
        students = students.where(m.Student.id == member.student_id)
    elif member.role == "guardian":
        students = students.where(m.Student.id.in_(select(m.GuardianLink.student_id).where(m.GuardianLink.guardian_id == member.guardian_id, m.GuardianLink.verified.is_(True))))
    else:
        students = students.where(m.Student.id.in_(select(m.Enrollment.student_id).where(m.Enrollment.status == "active", m.Enrollment.class_id.in_(select(m.Assignment.class_id).where(m.Assignment.teacher_id == member.teacher_id)))))
    records = db.scalars(students.order_by(m.Student.name).limit(100)).all()
    # DTO reduzido: não expõe nascimento, contatos ou relações familiares.
    return {"students": [{"id": student.id, "name": student.name} for student in records], "message": "Notas e frequência serão disponibilizadas em uma próxima etapa."}


@app.get(TENANT + "/accounts", response_model=list[s.AccountOut], tags=["Equipe e acesso"])
def accounts(member=Depends(membership), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    permit(member, {"director"})
    rows = db.execute(select(m.Membership, m.User).join(m.User, m.User.id == m.Membership.user_id).where(m.Membership.institution_id == member.institution_id, m.Membership.school_id == member.school_id).order_by(m.User.name).offset(offset).limit(limit)).all()
    return [{"id": row.id, "name": user.name, "email": user.email, "role": row.role} for row, user in rows]


@app.post(TENANT + "/accounts", response_model=s.AccountOut, status_code=201, tags=["Equipe e acesso"])
def create_account(payload: s.AccountIn, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, {"director"})
    links = {}
    if payload.role in {"teacher", "student", "guardian"}:
        model = {"teacher": m.Teacher, "student": m.Student, "guardian": m.Guardian}[payload.role]
        if not payload.person_id:
            raise HTTPException(422, "Selecione a pessoa vinculada à conta.")
        find(db, model, payload.person_id, member)
        links[payload.role + "_id"] = str(payload.person_id)
    elif payload.person_id:
        raise HTTPException(422, "Este perfil não utiliza vínculo de pessoa.")
    user = m.User(name=payload.name, email=str(payload.email).lower(), password_hash=password_hasher.hash(payload.password))
    db.add(user)
    db.flush()
    account = m.Membership(user_id=user.id, institution_id=member.institution_id, school_id=member.school_id, role=payload.role, **links)
    db.add(account)
    db.flush()
    audit(db, member, "accounts.create", account.id)
    return {"id": account.id, "name": user.name, "email": user.email, "role": account.role}


@app.delete(TENANT + "/accounts/{item_id}", status_code=204, tags=["Equipe e acesso"])
def revoke_account(item_id: UUID, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, {"director"})
    account = db.scalar(select(m.Membership).where(m.Membership.id == str(item_id), m.Membership.institution_id == member.institution_id, m.Membership.school_id == member.school_id).with_for_update())
    if not account:
        raise HTTPException(404, "Conta não encontrada.")
    if account.user_id == member.user_id:
        raise HTTPException(409, "Você não pode remover seu próprio acesso.")
    audit(db, member, "accounts.revoke", account.id)
    db.delete(account)
