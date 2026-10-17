"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, allRows, type Row } from "@/lib/api";
import {
  NegotiationSimulator,
  ScheduleTable,
  type ProposalSchedule,
} from "./negotiation";
import { Button } from "./ui/button";
type Module = {
  key: string;
  title: string;
  fields: Record<string, string>;
  statuses: string[];
  transitions: Record<string, string[]>;
};
type RecordItem = {
  proposal?: { schedule: ProposalSchedule[]; created_receivables: string[] };
  department_info?: { open: boolean; hours: string };
  id: string;
  title: string;
  student: string | null;
  data: Record<string, string>;
  status: string;
  version: number;
};
type Event = {
  actor?: string;
  id: string;
  action: string;
  data: Record<string, string>;
  created_at: string;
};
const states: Record<string, string> = {
  administered: "Administração registrada",
  progress: "Atualizar progresso",
  reserved: "Reservado",
  requested: "Solicitado",
  open: "Aberto",
  in_progress: "Em atendimento",
  resolved: "Resolvido",
  submitted: "Enviado",
  review: "Em análise",
  approved: "Aprovado",
  rejected: "Recusado",
  new: "Novo",
  contacted: "Contato realizado",
  enrolled: "Convertido em matrícula",
  closed: "Encerrado",
  draft: "Rascunho",
  published: "Publicado",
  archived: "Arquivado",
  ready: "Pronto para uso",
  active: "Ativo",
  loaned: "Emprestado",
  returned: "Devolvido",
  lost: "Extraviado",
  scheduled: "Programado",
  boarded: "Embarcou",
  delivered: "Desembarcou",
  cancelled: "Cancelado",
  pending: "Pendente",
  restructured: "Renegociado",
  paid: "Pago (manual)",
  recorded: "Registrado",
  settled: "Quitado (manual)",
  expected: "Previsto",
  entered: "Entrou",
  released: "Saída registrada",
  found: "Encontrado",
  claimed: "Retirado",
  donated: "Doado",
};
export function ServicesView({
  base,
  role,
  initialModule = "",
}: {
  base: string;
  role: string;
  initialModule?: string;
}) {
  const [consents, setConsents] = useState<
    {
      id: string;
      title: string;
      kind: string;
      purpose: string;
      archived: boolean;
    }[]
  >([]);
  const [modules, setModules] = useState<Module[]>([]),
    [selected, setSelected] = useState(initialModule),
    [items, setItems] = useState<RecordItem[]>([]),
    [students, setStudents] = useState<Row[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [books, setBooks] = useState<RecordItem[]>([]),
    [plans, setPlans] = useState<RecordItem[]>([]),
    [classes, setClasses] = useState<Row[]>([]),
    [departments, setDepartments] = useState<RecordItem[]>([]),
    [history, setHistory] = useState<Event[] | null>(null),
    [active, setActive] = useState<RecordItem | null>(null),
    [next, setNext] = useState("");
  const module = modules.find((m) => m.key === selected),
    family = ["guardian", "student"].includes(role),
    canTransition =
      !family &&
      !(
        ["office_hours", "contract_templates"].includes(selected) &&
        role !== "director"
      ) &&
      !(
        (role === "teacher" && ["calendar", "knowledge"].includes(selected)) ||
        (role === "secretary" &&
          ["plans", "questions", "calendar"].includes(selected))
      ),
    canCreate =
      canTransition ||
      (role === "guardian" &&
        [
          "tickets",
          "renewals",
          "store",
          "agreements",
          "library",
          "medication",
        ].includes(selected));
  const canComment =
    !family ||
    [
      "tickets",
      "renewals",
      "store",
      "agreements",
      "library",
      "pei",
      "health",
      "medication",
      "pei_goals",
      "care_events",
    ].includes(selected);
  useEffect(() => {
    if (["director", "secretary", "coordinator"].includes(role))
      allRows(base + "/classes")
        .then(setClasses)
        .catch((e) => setError(e.message));
    api<Module[]>(base + "/services")
      .then(setModules)
      .catch((e) => setError(e.message));
    (family || role === "teacher"
      ? api<{ students: Row[] }>(base + "/portal?limit=100").then(
          (d) => d.students,
        )
      : allRows(base + "/students")
    )
      .then(setStudents)
      .catch((e) => setError(e.message));
  }, [base, family]);
  async function load(key = selected) {
    setItems(await allRows<RecordItem>(base + "/services/" + key));
  }
  useEffect(() => {
    if (selected === "tickets")
      allRows<RecordItem>(base + "/services/office_hours")
        .then((d) => setDepartments(d.filter((d) => d.status === "active")))
        .catch((e) => setError(e.message));
    if (["moments", "medication"].includes(selected))
      allRows<{
        id: string;
        title: string;
        kind: string;
        purpose: string;
        archived: boolean;
      }>(base + "/notices")
        .then((n) =>
          setConsents(
            n.filter(
              (n) =>
                n.kind === "authorization" &&
                !n.archived &&
                n.purpose === (selected === "moments" ? "image" : "medication"),
            ),
          ),
        )
        .catch((e) => setError(e.message));
    if (selected === "pei_goals")
      allRows<RecordItem>(base + "/services/pei")
        .then(setPlans)
        .catch((e) => setError(e.message));
    if (selected === "library")
      allRows<RecordItem>(base + "/services/books")
        .then(setBooks)
        .catch((e) => setError(e.message));
    if (selected) load().catch((e) => setError(e.message));
  }, [selected]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (
      !active ||
      next ||
      (family &&
        ["books", "office_hours", "knowledge", "calendar"].includes(selected))
    )
      return;
    const timer = setInterval(() => {
      if (document.hidden) return;
      api<Event[]>(base + `/service-records/${active.id}/events`)
        .then(setHistory)
        .catch((e) => setError(e.message));
    }, 5000);
    return () => clearInterval(timer);
  }, [base, active?.id, next]);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!module) return;
    setBusy(true);
    setError("");
    const form = e.currentTarget,
      f = new FormData(form);
    try {
      if (active) {
        await api(
          next === "progress"
            ? base + `/pei-goals/${active.id}/progress`
            : base +
                `/service-records/${active.id}/` +
                (next ? "transition" : "comments"),
          {
            method: "POST",
            body: JSON.stringify(
              next === "progress"
                ? {
                    version: active.version,
                    current: String(f.get("current")),
                    note: f.get("note"),
                  }
                : next
                  ? {
                      version: active.version,
                      status: next,
                      note: f.get("note"),
                    }
                  : { text: f.get("note") },
            ),
          },
        );
        if (next) {
          setActive(null);
          setHistory(null);
        } else {
          setHistory(
            await api<Event[]>(base + `/service-records/${active.id}/events`),
          );
        }
        form.reset();
      } else {
        await api(base + "/services/" + selected, {
          method: "POST",
          body: JSON.stringify({
            title: f.get("title"),
            student_id: f.get("student") || null,
            class_id: f.get("class") || null,
            data: Object.fromEntries(
              Object.keys(module.fields).map((key) => [
                key,
                [
                  "scheduled_at",
                  "occurred_at",
                  "starts_at",
                  "ends_at",
                ].includes(key)
                  ? new Date(String(f.get(key))).toISOString()
                  : key === "amount_cents"
                    ? String(Math.round(Number(f.get(key)) * 100))
                    : String(f.get(key) || ""),
              ]),
            ),
          }),
        });
        form.reset();
      }
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Serviços escolares</h1>
          <p>
            Atendimentos, planejamento e operações com histórico de
            acompanhamento.
          </p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="panel">
        <label className="field">
          Serviço
          <select
            aria-label="Serviço"
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              setActive(null);
              setHistory(null);
              setError("");
            }}
          >
            <option value="">Escolha um serviço</option>
            {modules.map((m) => (
              <option key={m.key} value={m.key}>
                {m.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      {module && (
        <>
          <h2>{module.title}</h2>
          {["finance", "canteen"].includes(selected) && (
            <p className="learning-note">
              Controle manual de valores e recebimentos.
            </p>
          )}
          {selected === "contract_templates" && (
            <p>
              Escreva o texto aprovado pela escola. Campos disponíveis:{" "}
              {
                "{{aluno}}, {{responsavel}}, {{escola}}, {{ano_letivo}} e {{mensalidade}}"
              }
              . Publique uma nova versão para alterar condições; minutas já
              emitidas mantêm o texto original.
            </p>
          )}
          {selected === "renewals" && (
            <p>
              A aprovação registra a análise da solicitação. A secretaria
              conclui a matrícula no cadastro acadêmico.
            </p>
          )}
          {selected === "plans" && (
            <p>Informe os códigos BNCC adotados no currículo da escola.</p>
          )}
          {selected === "access" && (
            <p>
              A escola confere a identidade e a autorização antes de registrar a
              saída.
            </p>
          )}
          {role === "director" &&
            [
              "pei",
              "health",
              "pei_goals",
              "care_events",
              "medication",
            ].includes(selected) && (
              <SensitivePermissions
                base={base}
                category={selected.startsWith("pei") ? "pei" : "health"}
                students={students}
              />
            )}
          {selected === "agreements" &&
            ["director", "secretary", "guardian"].includes(role) && (
              <NegotiationSimulator
                base={base}
                students={students}
                onSaved={load}
              />
            )}
          {canCreate && !active && (
            <form onSubmit={save} className="panel record-form">
              <h3>Novo registro</h3>
              <label className="field">
                Título
                <input name="title" required minLength={3} maxLength={160} />
              </label>
              <label className="field">
                Aluno
                <select
                  aria-label="Aluno"
                  name="student"
                  required={[
                    "pei",
                    "health",
                    "pei_goals",
                    "care_events",
                    "medication",
                    "renewals",
                    "library",
                    "transport",
                    "finance",
                    "canteen",
                    "access",
                    "moments",
                    "store",
                    "agreements",
                    "library",
                  ].includes(selected)}
                >
                  <option value="">Selecione (quando aplicável)</option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              {selected === "calendar" && (
                <label className="field">
                  Turma (vazio = escola inteira ou aluno selecionado)
                  <select aria-label="Turma do evento" name="class">
                    <option value="">Toda a escola</option>
                    {classes.map((c) => (
                      <option value={c.id} key={c.id}>
                        {c.name} · {c.academic_year}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {Object.entries(module.fields).map(([key, label]) => (
                <label className="field" key={key}>
                  {key === "amount_cents" ? "Valor (R$)" : label}
                  {key === "request_type" ? (
                    <select aria-label="Modalidade" name={key}>
                      <option value="initial">Matrícula inicial</option>
                      <option value="renewal">Rematrícula</option>
                    </select>
                  ) : key === "department" &&
                    selected === "tickets" &&
                    departments.length ? (
                    <select aria-label="Setor" name={key} required>
                      <option value="">Selecione</option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.data.department}>
                          {d.title}
                        </option>
                      ))}
                    </select>
                  ) : key === "consent_notice" ? (
                    <select aria-label="Autorização" name={key} required>
                      <option value="">
                        Selecione a autorização publicada
                      </option>
                      {consents.map((n) => (
                        <option value={n.id} key={n.id}>
                          {n.title}
                        </option>
                      ))}
                    </select>
                  ) : key === "pei_id" ? (
                    <select aria-label="Plano PEI" name={key} required>
                      <option value="">Selecione o plano deste aluno</option>
                      {plans.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.title} · {p.student}
                        </option>
                      ))}
                    </select>
                  ) : [
                      "scheduled_at",
                      "occurred_at",
                      "starts_at",
                      "ends_at",
                    ].includes(key) ? (
                    <input name={key} type="datetime-local" required />
                  ) : ["target", "current"].includes(key) ? (
                    <input
                      name={key}
                      type="number"
                      min={0}
                      step="0.0001"
                      required
                    />
                  ) : key === "book" && selected === "library" ? (
                    <select aria-label="Livro / exemplar" name={key} required>
                      <option value="">Selecione um exemplar do acervo</option>
                      {books
                        .filter((b) => b.status === "active")
                        .map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.title} · {b.data.shelf}
                          </option>
                        ))}
                    </select>
                  ) : ["date", "due_date"].includes(key) ? (
                    <input name={key} type="date" required />
                  ) : key === "amount_cents" ? (
                    <input
                      name={key}
                      type="number"
                      step="0.01"
                      min={0.01}
                      required
                    />
                  ) : [
                      "amount_cents",
                      "academic_year",
                      "quantity",
                      "installments",
                    ].includes(key) ? (
                    <input name={key} type="number" min={1} required />
                  ) : (
                    <textarea
                      name={key}
                      required
                      maxLength={
                        selected === "contract_templates" && key === "clauses"
                          ? 30000
                          : 4000
                      }
                    />
                  )}
                </label>
              ))}
              <Button disabled={busy}>Salvar registro</Button>
            </form>
          )}
          {!items.length && (
            <p className="panel">Nenhum registro disponível.</p>
          )}
          {items.map((r) => (
            <article className="panel learning-body" key={r.id}>
              <h3>{r.title}</h3>
              {r.department_info && (
                <p>
                  {r.department_info.open
                    ? "Setor em expediente"
                    : "Mensagem recebida fora do expediente"}{" "}
                  · {r.department_info.hours}
                </p>
              )}
              <p>
                {r.student} · {states[r.status] || r.status}
              </p>
              {Object.entries(r.data).map(([key, value]) => (
                <div key={key}>
                  <strong>{module.fields[key] || key}</strong>
                  <p style={{ whiteSpace: "pre-wrap" }}>
                    {key === "book"
                      ? books.find((b) => b.id === value)?.title || value
                      : key === "amount_cents"
                        ? (Number(value) / 100).toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })
                        : value}
                  </p>
                </div>
              ))}
              {selected === "pei_goals" && (
                <div>
                  <label>
                    Progresso: {r.data.current} de {r.data.target} {r.data.unit}
                    <progress
                      value={Math.min(
                        Number(r.data.current),
                        Number(r.data.target),
                      )}
                      max={Number(r.data.target)}
                    />
                  </label>
                  {!family && r.status !== "archived" && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setActive(r);
                        setNext("progress");
                        setHistory(null);
                      }}
                    >
                      Atualizar progresso
                    </Button>
                  )}
                </div>
              )}
              {r.proposal && (
                <div>
                  <h4>Parcelas da proposta</h4>
                  <ScheduleTable schedule={r.proposal.schedule} />
                  {r.proposal.created_receivables.length > 0 && (
                    <p>Parcelas geradas no controle financeiro da escola.</p>
                  )}
                </div>
              )}
              <div className="learning-toolbar">
                <Button
                  variant="outline"
                  onClick={() => {
                    setActive(r);
                    setNext("");
                    if (
                      family &&
                      [
                        "books",
                        "office_hours",
                        "knowledge",
                        "calendar",
                      ].includes(selected)
                    ) {
                      setHistory([]);
                      return;
                    }
                    api<Event[]>(base + `/service-records/${r.id}/events`)
                      .then(setHistory)
                      .catch((e) => setError(e.message));
                  }}
                >
                  {family &&
                  ["books", "office_hours", "knowledge", "calendar"].includes(
                    selected,
                  )
                    ? "Ver documentos publicados"
                    : "Acompanhar / comentar"}
                </Button>
                {family &&
                  selected === "medication" &&
                  ["submitted", "scheduled"].includes(r.status) && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setActive(r);
                        setNext("cancelled");
                        setHistory(null);
                      }}
                    >
                      Cancelar solicitação
                    </Button>
                  )}
                {canTransition &&
                  (module.transitions[r.status] || []).map((status) => (
                    <Button
                      variant="outline"
                      key={status}
                      onClick={() => {
                        setActive(r);
                        setNext(status);
                        setHistory(null);
                      }}
                    >
                      {states[status] || status}
                    </Button>
                  ))}
              </div>
            </article>
          ))}
          {active && (
            <section className="panel">
              <h3>
                {active.title} · {next ? states[next] : "Acompanhamento"}
              </h3>
              {history?.map((e) => (
                <div className="learning-record" key={e.id}>
                  <small>
                    {new Date(e.created_at).toLocaleString("pt-BR")}
                  </small>
                  {Object.entries(e.data).map(([k, v]) => (
                    <p key={k}>
                      {k === "from"
                        ? "De"
                        : k === "to"
                          ? "Para"
                          : k === "note"
                            ? "Observação"
                            : "Comentário"}
                      : {states[v] || v}
                    </p>
                  ))}
                </div>
              ))}
              <Attachments
                base={base}
                record={active.id}
                writable={canComment}
              />
              {(canComment || next) && (
                <form onSubmit={save}>
                  {next === "progress" && (
                    <label className="field">
                      Valor atual
                      <input
                        type="number"
                        name="current"
                        min={0}
                        step="0.0001"
                        required
                        defaultValue={active.data.current}
                      />
                    </label>
                  )}
                  <label className="field">
                    {next ? "Motivo / comprovante da operação" : "Comentário"}
                    <textarea
                      name="note"
                      required
                      minLength={3}
                      maxLength={2000}
                    />
                  </label>
                  <Button disabled={busy}>
                    {next ? "Confirmar alteração" : "Adicionar comentário"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setActive(null);
                      setHistory(null);
                    }}
                  >
                    Fechar
                  </Button>
                </form>
              )}
              {!canComment && !next && (
                <Button variant="outline" onClick={() => setActive(null)}>
                  Fechar acompanhamento
                </Button>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
type Slot = {
  id: string;
  teacher: string;
  starts_at: string;
  ends_at: string;
  booked: boolean;
  student: string | null;
  can_cancel: boolean;
  version: number;
};
export function MeetingsView({ base, role }: { base: string; role: string }) {
  const [items, setItems] = useState<Slot[]>([]),
    [people, setPeople] = useState<Row[]>([]),
    [students, setStudents] = useState<Row[]>([]),
    [student, setStudent] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function load() {
    setItems(await allRows<Slot>(base + "/meetings"));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
    if (role !== "guardian")
      allRows(base + "/meeting-teachers")
        .then(setPeople)
        .catch((e) => setError(e.message));
    (role === "guardian" || role === "teacher"
      ? api<{ students: Row[] }>(base + "/portal?limit=100").then(
          (d) => d.students,
        )
      : allRows(base + "/students")
    )
      .then(setStudents)
      .catch((e) => setError(e.message));
  }, [base, role]); // eslint-disable-line react-hooks/exhaustive-deps
  async function act(path: string, body: unknown) {
    setBusy(true);
    setError("");
    try {
      await api(base + path, { method: "POST", body: JSON.stringify(body) });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Agenda de reuniões</h1>
          <p>
            Disponibilidade de professores e reservas individuais com as
            famílias.
          </p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {role !== "guardian" && (
        <form
          className="panel record-form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            act("/meetings", {
              teacher_id: f.get("teacher"),
              starts_at: new Date(String(f.get("start"))).toISOString(),
              ends_at: new Date(String(f.get("end"))).toISOString(),
            });
          }}
        >
          <h2>Abrir horário</h2>
          <label className="field">
            Professor
            <select aria-label="Professor" name="teacher" required>
              <option value="">Selecione</option>
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Início
            <input type="datetime-local" name="start" required />
          </label>
          <label className="field">
            Fim
            <input type="datetime-local" name="end" required />
          </label>
          <Button disabled={busy}>Disponibilizar horário</Button>
        </form>
      )}
      <label className="field">
        Aluno para reserva
        <select value={student} onChange={(e) => setStudent(e.target.value)}>
          <option value="">Selecione</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      {!items.length && (
        <p className="panel">Nenhum horário futuro disponível.</p>
      )}
      {items.map((s) => (
        <article className="panel" key={s.id}>
          <h2>{s.teacher}</h2>
          <p>
            {new Date(s.starts_at).toLocaleString("pt-BR")} –{" "}
            {new Date(s.ends_at).toLocaleTimeString("pt-BR")}
          </p>
          <p>
            {s.booked
              ? `Reservado${s.student ? " para " + s.student : ""}`
              : "Disponível"}
          </p>
          {!s.booked && role !== "teacher" && (
            <Button
              disabled={busy || !student}
              onClick={() =>
                act(`/meetings/${s.id}/book`, {
                  student_id: student,
                  version: s.version,
                })
              }
            >
              Reservar reunião
            </Button>
          )}
          {s.can_cancel && (
            <Button
              variant="outline"
              disabled={busy}
              onClick={() =>
                act(`/meetings/${s.id}/cancel`, { version: s.version })
              }
            >
              Cancelar reserva
            </Button>
          )}
        </article>
      ))}
    </div>
  );
}
function SensitivePermissions({
  base,
  category,
  students,
}: {
  base: string;
  category: string;
  students: Row[];
}) {
  const [staff, setStaff] = useState<Row[]>([]),
    [grants, setGrants] = useState<
      {
        id: string;
        student_id: string;
        user_id: string;
        category: string;
        active: boolean;
      }[]
    >([]),
    [message, setMessage] = useState("");
  async function load() {
    setGrants(await api(base + "/sensitive-grants"));
  }
  useEffect(() => {
    allRows(base + "/sensitive-staff")
      .then(setStaff)
      .catch((e) => setMessage(e.message));
    load().catch((e) => setMessage(e.message));
  }, [base]); // eslint-disable-line react-hooks/exhaustive-deps
  async function save(data: unknown) {
    try {
      await api(base + "/sensitive-grants", {
        method: "POST",
        body: JSON.stringify(data),
      });
      setMessage("Permissão atualizada.");
      await load();
    } catch (e) {
      setMessage((e as Error).message);
    }
  }
  return (
    <details className="panel">
      <summary>Gerenciar acesso aos dados sensíveis</summary>
      <p>
        Conceda acesso por aluno e profissional. A revogação vale para a próxima
        consulta.
      </p>
      {message && <p role="status">{message}</p>}
      <form
        className="record-form"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          save({
            student_id: f.get("student"),
            user_id: f.get("user"),
            category,
            active: true,
          });
        }}
      >
        <label className="field">
          Aluno
          <select aria-label="Aluno" name="student" required>
            <option value="">Selecione</option>
            {students.map((s) => (
              <option value={s.id} key={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Profissional
          <select name="user" required>
            <option value="">Selecione</option>
            {staff.map((s) => (
              <option value={s.id} key={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <Button>Conceder acesso</Button>
      </form>
      {grants
        .filter((g) => g.category === category && g.active)
        .map((g) => (
          <div className="learning-record" key={g.id}>
            {String(
              students.find((s) => s.id === g.student_id)?.name || "Aluno",
            )}{" "}
            ·{" "}
            {String(
              staff.find((s) => s.id === g.user_id)?.name || "Profissional",
            )}
            <Button
              variant="outline"
              onClick={() =>
                save({
                  student_id: g.student_id,
                  user_id: g.user_id,
                  category,
                  active: false,
                })
              }
            >
              Revogar acesso
            </Button>
          </div>
        ))}
    </details>
  );
}
export function Attachments({
  base,
  record,
  writable,
}: {
  base: string;
  record: string;
  writable: boolean;
}) {
  const [items, setItems] = useState<{ id: string; filename: string }[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function load() {
    setItems(await api(base + `/service-records/${record}/attachments`));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [record]); // eslint-disable-line react-hooks/exhaustive-deps
  async function upload(file: File) {
    setBusy(true);
    setError("");
    try {
      if (file.size > 2 * 1024 * 1024)
        throw new Error("Envie um arquivo de até 2 MB.");
      const reader = new FileReader();
      const encoded = await new Promise<string>((resolve, reject) => {
        reader.onload = () => resolve(String(reader.result).split(",")[1]);
        reader.onerror = () =>
          reject(new Error("Não foi possível ler o arquivo."));
        reader.readAsDataURL(file);
      });
      await api(base + `/service-records/${record}/attachments`, {
        method: "POST",
        body: JSON.stringify({ filename: file.name, base64: encoded }),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function download(id: string) {
    try {
      const d = await api<{
        filename: string;
        mime_type: string;
        base64: string;
      }>(base + `/attachments/${id}/download`);
      const url = URL.createObjectURL(
        new Blob([Uint8Array.from(atob(d.base64), (c) => c.charCodeAt(0))], {
          type: d.mime_type,
        }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = d.filename;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="learning-body">
      <h4>Anexos privados</h4>
      {error && <p role="alert">{error}</p>}
      {items.map((a) => (
        <Button variant="outline" key={a.id} onClick={() => download(a.id)}>
          Baixar {a.filename}
        </Button>
      ))}
      {writable && (
        <label className="field">
          Adicionar PDF, PNG ou JPEG (até 2 MB)
          <input
            disabled={busy}
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
            }}
          />
        </label>
      )}
    </section>
  );
}
