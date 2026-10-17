"use client";
import { useEffect, useState } from "react";
import { api, allRows } from "@/lib/api";
import { Button } from "./ui/button";
type Question = {
  id: string;
  title: string;
  status: string;
  data: { subject: string; prompt: string; options: string };
};
type Summary = {
  id: string;
  title: string;
  class: string;
  question_count: number;
};
type Detail = {
  id: string;
  title: string;
  class: string;
  instructions: string;
  questions: {
    id: string;
    title: string;
    prompt: string;
    options: string;
    answer: string;
    explanation: string;
  }[];
};
export function ExamsView({ base }: { base: string }) {
  const [questions, setQuestions] = useState<Question[]>([]),
    [assignments, setAssignments] = useState<{ id: string; name: string }[]>(
      [],
    ),
    [items, setItems] = useState<Summary[]>([]),
    [detail, setDetail] = useState<Detail | null>(null),
    [figures, setFigures] = useState<
      Record<string, { id: string; filename: string; mime_type: string }[]>
    >({}),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [correction, setCorrection] = useState<{
      correct: number;
      total: number;
      items: {
        number: number;
        correct: boolean;
        expected: string;
        explanation: string;
      }[];
    } | null>(null);
  async function load() {
    setItems(await allRows<Summary>(base + "/exams"));
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
    allRows<Question>(base + "/services/questions")
      .then((q) => setQuestions(q.filter((q) => q.status === "ready")))
      .catch((e) => setError(e.message));
    api<{ assignments: { id: string; name: string }[] }>(
      base + "/learning/options",
    )
      .then((o) => setAssignments(o.assignments))
      .catch((e) => setError(e.message));
  }, [base]); // eslint-disable-line react-hooks/exhaustive-deps
  async function attachments(q: string) {
    try {
      const files = await api<
        { id: string; filename: string; mime_type: string }[]
      >(base + `/service-records/${q}/attachments`);
      setFigures((old) => ({
        ...old,
        [q]: files.filter((f) =>
          ["image/png", "image/jpeg"].includes(f.mime_type),
        ),
      }));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function download(id: string, key: boolean) {
    try {
      const d = await api<{ filename: string; base64: string }>(
        base + `/exams/${id}/pdf?answer_key=${key}`,
      );
      const url = URL.createObjectURL(
        new Blob([Uint8Array.from(atob(d.base64), (c) => c.charCodeAt(0))], {
          type: "application/pdf",
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
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Provas e gabaritos</h1>
          <p>
            Monte provas a partir das questões revisadas e baixe o gabarito
            separadamente.
          </p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form
        className="panel record-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget),
            ids = f.getAll("questions").map(String);
          setBusy(true);
          setError("");
          try {
            const exam = await api<Detail>(base + "/exams", {
              method: "POST",
              body: JSON.stringify({
                title: f.get("title"),
                instructions: f.get("instructions"),
                assignment_id: f.get("assignment") || null,
                question_ids: ids,
                figures: Object.fromEntries(
                  ids
                    .map((id) => [id, f.get("figure_" + id)])
                    .filter(([, value]) => value),
                ),
                randomize: f.has("randomize"),
              }),
            });
            setDetail(exam);
            setCorrection(null);
            await load();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>Montar uma prova</h2>
        <label className="field">
          Título da prova
          <input name="title" minLength={3} maxLength={160} required />
        </label>
        <label className="field">
          Orientações para os alunos
          <textarea
            name="instructions"
            minLength={3}
            maxLength={2000}
            required
          />
        </label>
        <label className="field">
          Turma e disciplina (opcional)
          <select aria-label="Turma e disciplina da prova" name="assignment">
            <option value="">Prova sem turma definida</option>
            {assignments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-field">
          <input type="checkbox" name="randomize" /> Embaralhar a ordem das
          questões
        </label>
        <fieldset>
          <legend>Selecione até 50 questões prontas</legend>
          {questions.map((q) => (
            <div className="learning-record" key={q.id}>
              <div>
                <label className="checkbox-field">
                  <input type="checkbox" name="questions" value={q.id} />
                  {q.title} · {q.data.subject}
                </label>
                <p>{q.data.prompt}</p>
                <p style={{ whiteSpace: "pre-wrap" }}>{q.data.options}</p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => attachments(q.id)}
                >
                  Escolher figura da questão
                </Button>
                {figures[q.id] && (
                  <label className="field">
                    Figura
                    <select name={"figure_" + q.id}>
                      <option value="">Sem figura</option>
                      {figures[q.id].map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.filename}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
            </div>
          ))}
        </fieldset>
        <Button disabled={busy || !questions.length}>
          Salvar prova e ordem do gabarito
        </Button>
      </form>
      {items.map((e) => (
        <article className="panel" key={e.id}>
          <h2>{e.title}</h2>
          <p>
            {e.class} · {e.question_count} questões
          </p>
          <div className="learning-toolbar">
            <Button variant="outline" onClick={() => download(e.id, false)}>
              PDF da prova sem gabarito
            </Button>
            <Button variant="outline" onClick={() => download(e.id, true)}>
              PDF do gabarito docente
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                api<Detail>(base + "/exams/" + e.id)
                  .then((d) => {
                    setDetail(d);
                    setCorrection(null);
                  })
                  .catch((e) => setError(e.message))
              }
            >
              Conferir respostas desta prova
            </Button>
          </div>
        </article>
      ))}
      {detail && (
        <section className="panel">
          <h2>{detail.title} · Conferência manual</h2>
          <p>
            A ordem e as respostas esperadas ficam preservadas nesta prova. A
            conferência não lança notas no diário automaticamente.
          </p>
          <form
            className="record-form"
            key={detail.id}
            onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              setBusy(true);
              try {
                setCorrection(
                  await api(base + `/exams/${detail.id}/correct`, {
                    method: "POST",
                    body: JSON.stringify({
                      answers: detail.questions.map((_, i) =>
                        String(f.get("answer_" + i) || ""),
                      ),
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
            {detail.questions.map((q, i) => (
              <label className="field" key={q.id}>
                Questão {i + 1} · {q.title}
                <input name={"answer_" + i} maxLength={4000} />
              </label>
            ))}
            <Button disabled={busy}>Conferir folha digitada</Button>
          </form>
          {correction && (
            <div>
              <h3>
                {correction.correct} de {correction.total} acertos
              </h3>
              {correction.items.map((r) => (
                <p key={r.number}>
                  Questão {r.number}: {r.correct ? "Correta" : "Incorreta"} ·
                  Gabarito: {r.expected} · {r.explanation}
                </p>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
