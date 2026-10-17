"use client";
import { useEffect, useState } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { Button } from "./ui/button";
type Alert = {
  student_id: string;
  student: string;
  subject: string;
  term: string;
  reasons: string[];
  average: string | null;
  attendance: string | null;
};
type Schedule = {
  id: string;
  title: string;
  academic_year: number;
  rows: {
    day: number;
    period: number;
    class: string;
    subject: string;
    teacher: string;
    room: string;
  }[];
};
export function InsightsView({
  base,
  mode,
  role,
}: {
  base: string;
  mode: string;
  role: string;
}) {
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [alerts, setAlerts] = useState<Alert[]>([]),
    [schedules, setSchedules] = useState<Schedule[]>([]),
    [assignments, setAssignments] = useState<Row[]>([]),
    [names, setNames] = useState<Record<string, string>>({}),
    [questions, setQuestions] = useState<
      {
        id: string;
        title: string;
        status: string;
        data: { prompt: string; options: string };
      }[]
    >([]),
    [correction, setCorrection] = useState<{
      correct: number;
      total: number;
      items: {
        title: string;
        correct: boolean;
        expected: string;
        explanation: string;
      }[];
    } | null>(null),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (mode === "timetables") {
      allRows<Schedule>(base + "/timetables")
        .then(setSchedules)
        .catch((e) => setError(e.message));
      Promise.all([
        allRows(base + "/assignments"),
        allRows(base + "/classes"),
        allRows(base + "/teachers"),
        allRows(base + "/subjects"),
      ])
        .then(([a, ...lists]) => {
          setAssignments(a);
          setNames(
            Object.fromEntries(lists.flat().map((r) => [r.id, String(r.name)])),
          );
        })
        .catch((e) => setError(e.message));
    }
    if (mode === "correction")
      allRows<{
        id: string;
        title: string;
        status: string;
        data: { prompt: string; options: string };
      }>(base + "/services/questions")
        .then((q) => setQuestions(q.filter((q) => q.status === "ready")))
        .catch((e) => setError(e.message));
  }, [base, mode]);
  const titles: Record<string, string> = {
    alerts: "Alertas pedagógicos",
    timetables: "Grade de horários",
    correction: "Correção por gabarito",
    units: "Unidades escolares",
  };
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>{titles[mode]}</h1>
          <p>
            {mode === "alerts"
              ? "Indicadores baseados nas regras de avaliação e nas faltas registradas."
              : mode === "timetables"
                ? "Gere uma proposta sem conflitos de professor, turma e sala."
                : mode === "correction"
                  ? "Confira respostas digitadas usando questões prontas do banco."
                  : "Cadastre unidades e selecione a unidade e o perfil no topo do portal."}
          </p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {mode === "units" && (
        <form
          className="panel record-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            setBusy(true);
            try {
              const r = await api<{ message: string }>(base + "/units", {
                method: "POST",
                body: JSON.stringify({ name: f.get("name") }),
              });
              setMessage(r.message);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label className="field">
            Nome da nova unidade
            <input name="name" minLength={3} maxLength={160} required />
          </label>
          <Button disabled={busy}>Criar unidade</Button>
        </form>
      )}
      {mode === "alerts" && (
        <>
          <form
            className="panel record-form"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              const f = new FormData(e.currentTarget);
              try {
                setAlerts(
                  await api(
                    base +
                      `/alerts?academic_year=${f.get("year")}&consecutive=${f.get("consecutive")}`,
                  ),
                );
                setLoaded(true);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label className="field">
              Ano letivo
              <input
                type="number"
                name="year"
                defaultValue={new Date().getFullYear()}
                min={2000}
                max={2100}
                required
              />
            </label>
            <label className="field">
              Faltas consecutivas (aulas)
              <input
                type="number"
                name="consecutive"
                defaultValue={3}
                min={2}
                max={30}
                required
              />
            </label>
            <Button disabled={busy}>Consultar indicadores</Button>
          </form>
          <p>
            Os indicadores apoiam a revisão da coordenação. Verifique os
            lançamentos e o contexto de cada aluno antes de agir.
          </p>
          {loaded && !alerts.length && (
            <p className="panel">
              Nenhum alerta para os critérios consultados.
            </p>
          )}
          {alerts.map((a, i) => (
            <article className="panel" key={i}>
              <h2>{a.student}</h2>
              <p>
                {a.subject} · {a.term}
              </p>
              <p>
                Média: {a.average ?? "Pendente"} · Frequência:{" "}
                {a.attendance ?? "Pendente"}%
              </p>
              <ul>
                {a.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </article>
          ))}
        </>
      )}
      {mode === "correction" && (
        <form
          className="panel record-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            const selected = questions.filter((q) => f.has("include_" + q.id));
            setBusy(true);
            try {
              setCorrection(
                await api(base + "/answer-sheets/correct", {
                  method: "POST",
                  body: JSON.stringify({
                    question_ids: selected.map((q) => q.id),
                    answers: selected.map((q) => String(f.get(q.id) || "")),
                  }),
                }),
              );
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {!questions.length && (
            <p>
              Marque questões como prontas no banco de questões para corrigir
              uma folha de respostas.
            </p>
          )}
          {questions.map((q) => (
            <div key={q.id}>
              <label>
                <input type="checkbox" name={"include_" + q.id} />
                {q.title}
              </label>
              <p>{q.data.prompt}</p>
              <p style={{ whiteSpace: "pre-wrap" }}>{q.data.options}</p>
              <label className="field">
                Resposta marcada
                <input name={q.id} maxLength={200} />
              </label>
            </div>
          ))}
          <Button disabled={busy || !questions.length}>
            Conferir respostas
          </Button>
          {correction && (
            <section>
              <h2>
                {correction.correct} de {correction.total} acertos
              </h2>
              {correction.items.map((r, i) => (
                <p key={i}>
                  {r.title}: {r.correct ? "Correta" : "Incorreta"} · Gabarito:{" "}
                  {r.expected} · {r.explanation}
                </p>
              ))}
            </section>
          )}
        </form>
      )}
      {mode === "timetables" && (
        <>
          {role !== "secretary" && (
            <form
              className="panel record-form"
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError("");
                const f = new FormData(e.currentTarget);
                try {
                  const r = await api<Schedule>(base + "/timetables", {
                    method: "POST",
                    body: JSON.stringify({
                      title: f.get("title"),
                      academic_year: Number(f.get("year")),
                      periods_per_day: Number(f.get("periods")),
                      demands: assignments
                        .filter((a) => Number(f.get(a.id + "_count")) > 0)
                        .map((a) => ({
                          assignment_id: a.id,
                          room: f.get(a.id + "_room"),
                          periods: Number(f.get(a.id + "_count")),
                          blocked: String(f.get(a.id + "_blocked") || "")
                            .split(",")
                            .filter((v) => v.trim())
                            .map(Number),
                        })),
                    }),
                  });
                  setSchedules((old) => [r, ...old]);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label className="field">
                Nome da proposta
                <input name="title" required minLength={3} />
              </label>
              <label className="field">
                Ano
                <input
                  name="year"
                  type="number"
                  defaultValue={new Date().getFullYear()}
                  required
                />
              </label>
              <label className="field">
                Aulas por dia (segunda a sexta)
                <input
                  name="periods"
                  type="number"
                  min={1}
                  max={10}
                  defaultValue={6}
                  required
                />
              </label>
              <p>
                Preencha a quantidade semanal das atribuições que deseja
                incluir. Indisponibilidades são índices de horário: com 6
                aulas/dia, segunda = 0 a 5, terça = 6 a 11, e assim por diante.
              </p>
              {assignments.map((a) => (
                <fieldset key={a.id} className="learning-record">
                  <legend>
                    {names[String(a.class_id)]} · {names[String(a.subject_id)]}{" "}
                    · {names[String(a.teacher_id)]}
                  </legend>
                  <label className="field">
                    Aulas semanais
                    <input
                      name={a.id + "_count"}
                      type="number"
                      min={0}
                      max={30}
                      defaultValue={0}
                    />
                  </label>
                  <label className="field">
                    Sala
                    <input
                      name={a.id + "_room"}
                      defaultValue={names[String(a.class_id)]}
                      maxLength={60}
                    />
                  </label>
                  <label className="field">
                    Horários indisponíveis do professor (separados por vírgula)
                    <input name={a.id + "_blocked"} />
                  </label>
                </fieldset>
              ))}
              <Button disabled={busy}>Gerar proposta de grade</Button>
            </form>
          )}
          {schedules.map((s) => (
            <section className="panel" key={s.id}>
              <h2>
                {s.title} · {s.academic_year}
              </h2>
              <p>Proposta para revisão da coordenação.</p>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dia</th>
                      <th>Aula</th>
                      <th>Turma</th>
                      <th>Disciplina</th>
                      <th>Professor</th>
                      <th>Sala</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...s.rows]
                      .sort((a, b) => a.day - b.day || a.period - b.period)
                      .map((r, i) => (
                        <tr key={i}>
                          <td>
                            {
                              ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"][
                                r.day - 1
                              ]
                            }
                          </td>
                          <td>{r.period}</td>
                          <td>{r.class}</td>
                          <td>{r.subject}</td>
                          <td>{r.teacher}</td>
                          <td>{r.room}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  );
}
