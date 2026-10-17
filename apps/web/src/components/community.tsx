"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { ContractDraftForm } from "./contracts";
import { Button } from "./ui/button";
type Notice = {
  id: string;
  title: string;
  body: string;
  kind: string;
  options: string[];
  deadline: string | null;
  archived: boolean;
  students: { id: string; name: string }[];
  responses: {
    student_id: string;
    viewer_role: string;
    answer: string | null;
    read_at: string;
  }[];
};
type Receipt = {
  student: string;
  read: boolean;
  responses: { user: string; viewer_role: string; answer: string | null }[];
};
const labels: Record<string, string> = {
  yes: "Autorizo",
  no: "Não autorizo",
  withdraw: "Autorização retirada",
};
export function CommunityView({ base, role }: { base: string; role: string }) {
  const manager = ["director", "secretary", "coordinator"].includes(role);
  const [items, setItems] = useState<Notice[]>([]),
    [classes, setClasses] = useState<Row[]>([]),
    [students, setStudents] = useState<Row[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [kind, setKind] = useState("notice"),
    [receipts, setReceipts] = useState<Receipt[] | null>(null);
  async function load() {
    setItems(await allRows<Notice>(base + "/notices"));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
    if (manager)
      allRows(base + "/students")
        .then(setStudents)
        .catch((e) => setError(e.message));
    if (manager)
      allRows(base + "/classes")
        .then(setClasses)
        .catch((e) => setError(e.message));
  }, [base]); // eslint-disable-line react-hooks/exhaustive-deps
  async function act(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    try {
      await api(base + path, {
        method: "POST",
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      await load();
      setMessage("Registro salvo.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function publish(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      f = new FormData(form);
    await act("/notices", {
      title: f.get("title"),
      body: f.get("body"),
      kind,
      purpose: kind === "authorization" ? f.get("purpose") : "general",
      academic_year: Number(f.get("year")),
      class_id: f.get("class") || null,
      student_id: f.get("student") || null,
      shift: f.get("shift") || null,
      options:
        kind === "poll"
          ? String(f.get("options"))
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean)
          : [],
      deadline: f.get("deadline")
        ? new Date(String(f.get("deadline"))).toISOString()
        : null,
    });
  }
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Mural e autorizações</h1>
          <p>
            Comunicados por turma e turno, confirmação de leitura e respostas
            dos responsáveis.
          </p>
        </div>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {manager && (
        <form onSubmit={publish} className="panel record-form">
          <h2>Publicar comunicado</h2>
          <label className="field">
            Título
            <input name="title" required minLength={3} maxLength={160} />
          </label>
          <label className="field">
            Mensagem
            <textarea name="body" required minLength={3} maxLength={6000} />
          </label>
          <label className="field">
            Tipo
            <select
              aria-label="Tipo"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="notice">Aviso</option>
              <option value="authorization">Autorização</option>
              <option value="poll">Enquete</option>
            </select>
          </label>
          <label className="field">
            Ano letivo
            <input
              name="year"
              type="number"
              defaultValue={new Date().getFullYear()}
              min={2000}
              max={2100}
              required
            />
          </label>
          <label className="field">
            Aluno específico (opcional)
            <select aria-label="Aluno específico" name="student">
              <option value="">Público por turma / turno</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Turma
            <select aria-label="Turma" name="class">
              <option value="">Todas as turmas</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {String(c.name)} · {c.academic_year}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Turno
            <select aria-label="Turno" name="shift">
              <option value="">Todos</option>
              <option value="morning">Manhã</option>
              <option value="afternoon">Tarde</option>
              <option value="evening">Noite</option>
              <option value="full">Integral</option>
            </select>
          </label>
          {kind === "authorization" && (
            <label className="field">
              Finalidade
              <select aria-label="Finalidade" name="purpose">
                <option value="general">Atividade escolar / geral</option>
                <option value="image">Uso de imagem no mural privado</option>
                <option value="medication">
                  Medicação conforme prescrição
                </option>
                <option value="pickup">Retirada por terceiro</option>
              </select>
            </label>
          )}
          {kind === "poll" && (
            <label className="field">
              Opções (uma por linha)
              <textarea
                name="options"
                required
                placeholder={"Primeira opção\nSegunda opção"}
              />
            </label>
          )}
          <label className="field">
            Prazo de resposta (opcional)
            <input name="deadline" type="datetime-local" />
          </label>
          <p>
            O texto e o público ficam registrados após a publicação. Para
            corrigir, arquive e publique um novo comunicado.
          </p>
          <Button disabled={busy}>Publicar no mural</Button>
        </form>
      )}
      {!items.length && (
        <div className="panel">Nenhum comunicado disponível.</div>
      )}
      {items.map((n) => (
        <article className="panel learning-body" key={n.id}>
          <h2>
            {n.title}
            {n.archived ? " · Arquivado" : ""}
          </h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{n.body}</p>
          {n.deadline && (
            <p>Prazo: {new Date(n.deadline).toLocaleString("pt-BR")}</p>
          )}
          {manager ? (
            <div className="learning-toolbar">
              <span>
                {n.students.length} alunos no público · Código: {n.id}
              </span>
              <Button
                variant="outline"
                onClick={() =>
                  api<Receipt[]>(base + `/notices/${n.id}/receipts`)
                    .then(setReceipts)
                    .catch((e) => setError(e.message))
                }
              >
                Ver leituras e respostas
              </Button>
              {!n.archived && (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => act(`/notices/${n.id}/archive`)}
                >
                  Arquivar
                </Button>
              )}
            </div>
          ) : (
            n.students.map((s) => {
              const r = n.responses.find((r) => r.student_id === s.id);
              const confirmed =
                !!r &&
                (role !== "guardian"
                  ? r.viewer_role !== "legacy"
                  : r.viewer_role === "guardian");
              return (
                <div key={s.id} className="learning-record">
                  <strong>{s.name}</strong>
                  <p>
                    {confirmed ? "Leitura confirmada" : "Leitura pendente"}
                    {r?.answer ? ` · ${labels[r.answer] || r.answer}` : ""}
                  </p>
                  <Button
                    disabled={busy || confirmed}
                    variant="outline"
                    onClick={() =>
                      act(`/notices/${n.id}/respond`, { student_id: s.id })
                    }
                  >
                    Confirmar leitura
                  </Button>
                  {role === "guardian" && n.kind !== "notice" && (
                    <div className="learning-toolbar">
                      {(n.kind === "poll"
                        ? n.options
                        : ["yes", "no", "withdraw"]
                      ).map((answer) => (
                        <Button
                          variant="outline"
                          disabled={busy}
                          key={answer}
                          onClick={() =>
                            act(`/notices/${n.id}/respond`, {
                              student_id: s.id,
                              answer,
                            })
                          }
                        >
                          {labels[answer] || answer}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </article>
      ))}
      {receipts && (
        <section className="panel">
          <h2>Leituras e respostas</h2>
          <Button variant="outline" onClick={() => setReceipts(null)}>
            Fechar resultados
          </Button>
          {receipts.map((r, i) => (
            <div className="learning-record" key={i}>
              <strong>{r.student}</strong>
              <p>
                {r.read
                  ? "Responsável confirmou leitura"
                  : "Aguardando confirmação do responsável"}
              </p>
              {r.responses.map((s, j) => (
                <p key={j}>
                  {s.user}:{" "}
                  {s.answer
                    ? labels[s.answer] || s.answer
                    : "Leitura confirmada"}
                </p>
              ))}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
type Document = {
  id: string;
  student: string;
  title: string;
  issued_at: string;
  revoked: boolean;
  reason: string | null;
};
export function DocumentsView({ base, role }: { base: string; role: string }) {
  const manager = ["director", "secretary"].includes(role),
    [items, setItems] = useState<Document[]>([]),
    [students, setStudents] = useState<Row[]>([]),
    [terms, setTerms] = useState<Row[]>([]),
    [years, setYears] = useState<Row[]>([]),
    [academicYear, setAcademicYear] = useState(new Date().getFullYear()),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [revoke, setRevoke] = useState("");
  async function load() {
    setItems(await allRows<Document>(base + "/documents"));
  }
  useEffect(() => {
    if (manager) {
      allRows(base + "/academic-terms")
        .then(setTerms)
        .catch((e) => setError(e.message));
      allRows(base + "/academic-years")
        .then(setYears)
        .catch((e) => setError(e.message));
    }
    load().catch((e) => setError(e.message));
    if (manager)
      allRows(base + "/students")
        .then(setStudents)
        .catch((e) => setError(e.message));
  }, [base]); // eslint-disable-line react-hooks/exhaustive-deps
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      await api(base + "/documents" + (revoke ? `/${revoke}/revoke` : ""), {
        method: "POST",
        body: JSON.stringify(
          revoke
            ? { reason: f.get("reason") }
            : {
                student_id: f.get("student"),
                kind: f.get("kind"),
                academic_year: Number(f.get("year")),
                term_id: ["report", "attendance"].includes(
                  String(f.get("kind")),
                )
                  ? f.get("term") || null
                  : null,
              },
        ),
      });
      setRevoke("");
      await load();
      setMessage(
        revoke
          ? "Documento revogado."
          : "Documento emitido. Baixe o PDF na lista abaixo.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function download(id: string) {
    try {
      const d = await api<{ base64: string; filename: string }>(
        base + `/documents/${id}/download`,
      );
      const bytes = Uint8Array.from(atob(d.base64), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(
        new Blob([bytes], { type: "application/pdf" }),
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
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Documentos escolares</h1>
          <p>
            Declarações e resultados publicados em PDF com QR Code de
            autenticidade.
          </p>
        </div>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {manager && (
        <form className="panel record-form" onSubmit={submit}>
          <h2>{revoke ? "Revogar documento" : "Emitir documento"}</h2>
          {revoke ? (
            <label className="field">
              Motivo
              <textarea
                name="reason"
                required
                minLength={10}
                maxLength={1000}
              />
            </label>
          ) : (
            <>
              <label className="field">
                Aluno
                <select aria-label="Aluno" name="student" required>
                  <option value="">Selecione</option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Documento
                <select aria-label="Documento" name="kind">
                  <option value="enrollment">Declaração de matrícula</option>
                  <option value="attendance">Declaração de frequência</option>
                  <option value="report">Boletim publicado</option>
                  <option value="history">
                    Histórico de resultados anuais publicados
                  </option>
                </select>
              </label>
              <label className="field">
                Período do boletim / frequência (opcional)
                <select
                  aria-label="Período do documento"
                  name="term"
                  key={academicYear}
                >
                  <option value="">Todos os períodos publicados do ano</option>
                  {terms
                    .filter(
                      (t) =>
                        Number(
                          years.find((y) => y.id === t.academic_year_id)?.year,
                        ) === academicYear,
                    )
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                </select>
              </label>
              <label className="field">
                Ano letivo
                <input
                  name="year"
                  type="number"
                  min={2000}
                  max={2100}
                  value={academicYear}
                  onChange={(e) => setAcademicYear(Number(e.target.value))}
                  required
                />
              </label>
            </>
          )}
          <Button disabled={busy}>
            {revoke ? "Confirmar revogação" : "Emitir PDF"}
          </Button>
          {revoke && (
            <Button
              type="button"
              variant="outline"
              onClick={() => setRevoke("")}
            >
              Cancelar
            </Button>
          )}
        </form>
      )}
      {manager && (
        <ContractDraftForm base={base} students={students} onIssued={load} />
      )}
      {!items.length && <p className="panel">Nenhum documento emitido.</p>}
      {items.map((d) => (
        <article className="panel" key={d.id} data-document-id={d.id}>
          <h2>{d.title}</h2>
          <p>
            {d.student} · {new Date(d.issued_at).toLocaleString("pt-BR")}
          </p>
          {d.revoked && <p>Revogado: {d.reason}</p>}
          <div className="learning-toolbar">
            <Button variant="outline" onClick={() => download(d.id)}>
              Baixar PDF
            </Button>
            {manager && !d.revoked && (
              <Button variant="outline" onClick={() => setRevoke(d.id)}>
                Revogar
              </Button>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
