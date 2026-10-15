"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { Attachments } from "./services";
import { Button } from "./ui/button";

type Consultation = {
  id: string;
  student: string;
  student_id: string;
  professional: string;
  can_write: boolean;
  version: number;
  data: {
    occurred_at: string;
    kind: string;
    observations: string;
    analysis: string;
    plan: string;
    next_visit: string | null;
    professional_registration: string;
  };
};
type Evolution = {
  id: string;
  actor: string;
  created_at: string;
  data: { text?: string };
};
const kinds: Record<string, string> = {
  initial: "Acolhimento inicial",
  follow_up: "Acompanhamento",
  assessment: "Avaliação",
  family: "Atendimento à família",
  referral: "Encaminhamento",
};
export function PsychologyView({ base, role }: { base: string; role: string }) {
  const [students, setStudents] = useState<Row[]>([]),
    [student, setStudent] = useState(""),
    [records, setRecords] = useState<Consultation[]>([]),
    [selected, setSelected] = useState<Consultation | null>(null),
    [history, setHistory] = useState<Evolution[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const psychologist = role === "psychologist";
  useEffect(() => {
    let active = true;
    allRows<Row>(base + "/psychology/students")
      .then((s) => {
        if (active) setStudents(s);
      })
      .catch((e) => setError(e.message));
    return () => {
      active = false;
    };
  }, [base]);
  async function load() {
    setRecords(
      await allRows<Consultation>(
        base + "/psychology" + (student ? "?student_id=" + student : ""),
      ),
    );
  }
  useEffect(() => {
    let active = true;
    setSelected(null);
    setHistory([]);
    setError("");
    allRows<Consultation>(
      base + "/psychology" + (student ? "?student_id=" + student : ""),
    )
      .then((r) => {
        if (active) setRecords(r);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [base, student]);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      f = new FormData(form);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api(base + "/psychology", {
        method: "POST",
        body: JSON.stringify({
          student_id: student,
          kind: f.get("kind"),
          occurred_at: new Date(String(f.get("occurred_at"))).toISOString(),
          observations: f.get("observations"),
          analysis: f.get("analysis"),
          plan: f.get("plan"),
          professional_registration: f.get("professional_registration"),
          next_visit: f.get("next_visit")
            ? new Date(String(f.get("next_visit"))).toISOString()
            : null,
        }),
      });
      form.reset();
      await load();
      setMessage(
        "Atendimento registrado. Alterações posteriores são acrescentadas no histórico.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function open(r: Consultation) {
    setBusy(true);
    setSelected(r);
    setHistory([]);
    setError("");
    try {
      setHistory(
        await api<Evolution[]>(base + `/service-records/${r.id}/events`),
      );
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
          <h1>Psicologia escolar</h1>
          <p>
            Atendimentos e acompanhamento individual. Consulta restrita ao
            psicólogo autor e à direção.
          </p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="success" role="status">
          {message}
        </p>
      )}
      <section className="panel record-form">
        <label className="field">
          Aluno
          <select
            aria-label="Aluno do acompanhamento"
            value={student}
            disabled={busy}
            onChange={(e) => {
              setStudent(e.target.value);
              setMessage("");
            }}
          >
            <option value="">Todos os alunos</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <p>
          Os registros e anexos deste módulo não aparecem no portal da família
          nem nos módulos de professores ou secretaria.
        </p>
      </section>
      {psychologist && student && (
        <form className="panel record-form" onSubmit={save}>
          <h2>Registrar atendimento</h2>
          <label className="field">
            Data e hora do atendimento
            <input
              aria-label="Data e hora do atendimento"
              name="occurred_at"
              type="datetime-local"
              required
            />
          </label>
          <label className="field">
            Tipo de atendimento
            <select name="kind">
              {Object.entries(kinds).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Registro profissional (opcional)
            <input name="professional_registration" maxLength={40} />
          </label>
          {[
            ["observations", "Observações do atendimento", 8000],
            ["analysis", "Análise do psicólogo", 8000],
            ["plan", "Plano de acompanhamento", 4000],
          ].map(([key, label, max]) => (
            <label className="field" key={key}>
              {label}
              <textarea
                aria-label={String(label)}
                name={String(key)}
                minLength={3}
                maxLength={Number(max)}
                required
                rows={4}
              />
            </label>
          ))}
          <label className="field">
            Próximo retorno (opcional)
            <input name="next_visit" type="datetime-local" />
          </label>
          <Button disabled={busy}>
            {busy ? "Salvando…" : "Registrar atendimento"}
          </Button>
        </form>
      )}
      <section className="panel record-form">
        <h2>Histórico de atendimentos</h2>
        {!records.length && (
          <p>Nenhum atendimento registrado para esta seleção.</p>
        )}
        {records.map((r) => (
          <article className="learning-record" key={r.id}>
            <div>
              <strong>{r.student}</strong>
              <p>
                {kinds[r.data.kind]} ·{" "}
                {new Date(r.data.occurred_at).toLocaleString("pt-BR")}
              </p>
              <p>
                {r.professional}
                {r.data.professional_registration
                  ? " · " + r.data.professional_registration
                  : ""}
              </p>
              {r.data.next_visit && (
                <p>
                  Retorno: {new Date(r.data.next_visit).toLocaleString("pt-BR")}
                </p>
              )}
            </div>
            <Button variant="outline" disabled={busy} onClick={() => open(r)}>
              Consultar atendimento
            </Button>
          </article>
        ))}
      </section>
      {selected && (
        <section className="panel record-form">
          <h2>Atendimento · {selected.student}</h2>
          <h3>Observações</h3>
          <p className="preserve-lines">{selected.data.observations}</p>
          <h3>Análise</h3>
          <p className="preserve-lines">{selected.data.analysis}</p>
          <h3>Plano de acompanhamento</h3>
          <p className="preserve-lines">{selected.data.plan}</p>
          <h3>Evoluções e complementos</h3>
          {history.map((h) => (
            <article key={h.id}>
              <small>
                {h.actor} · {new Date(h.created_at).toLocaleString("pt-BR")}
              </small>
              <p className="preserve-lines">{h.data.text}</p>
            </article>
          ))}
          {selected.can_write && (
            <form
              className="record-form"
              onSubmit={async (e) => {
                e.preventDefault();
                const f = e.currentTarget;
                setBusy(true);
                setError("");
                try {
                  const updated = await api<Consultation>(
                    base + `/psychology/${selected.id}/notes`,
                    {
                      method: "POST",
                      body: JSON.stringify({
                        version: selected.version,
                        text: new FormData(f).get("text"),
                      }),
                    },
                  );
                  setSelected(updated);
                  setHistory(
                    await api<Evolution[]>(
                      base + `/service-records/${selected.id}/events`,
                    ),
                  );
                  f.reset();
                  await load();
                } catch (err) {
                  setError((err as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label className="field">
                Acrescentar evolução ou retificação
                <textarea
                  aria-label="Acrescentar evolução ou retificação"
                  name="text"
                  required
                  minLength={3}
                  maxLength={8000}
                />
              </label>
              <Button disabled={busy}>Salvar complemento</Button>
            </form>
          )}
          <Attachments
            key={selected.id}
            base={base}
            record={selected.id}
            writable={selected.can_write}
          />
          <Button variant="outline" onClick={() => setSelected(null)}>
            Fechar atendimento
          </Button>
        </section>
      )}
    </div>
  );
}
