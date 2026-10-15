"use client";
import { useEffect, useState } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { Button } from "./ui/button";
type Receivable = {
  id: string;
  title: string;
  student_id: string;
  status: string;
  data: { amount_cents: string; due_date: string };
};
export type ProposalSchedule = {
  number: number;
  due_date: string;
  amount_cents: number;
};
type Quote = {
  principal_cents: number;
  total_cents: number;
  interest_percent: string;
  schedule: ProposalSchedule[];
};
const money = (c: number) =>
  (c / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export function NegotiationSimulator({
  base,
  students,
  onSaved,
}: {
  base: string;
  students: Row[];
  onSaved: () => Promise<void>;
}) {
  const [student, setStudent] = useState(""),
    [sources, setSources] = useState<Receivable[]>([]),
    [quote, setQuote] = useState<Quote | null>(null),
    [payload, setPayload] = useState<unknown>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    allRows<Receivable>(base + "/services/finance")
      .then(setSources)
      .catch((e) => setError(e.message));
  }, [base]);
  return (
    <section className="panel record-form">
      <h3>Simular parcelamento</h3>
      <p>
        Simulação sem juros. A proposta será analisada pela escola; a aprovação
        substitui as contas selecionadas pelas parcelas aprovadas no controle
        interno.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <label className="field">
        Aluno da negociação
        <select
          aria-label="Aluno da negociação"
          value={student}
          onChange={(e) => {
            setStudent(e.target.value);
            setQuote(null);
            setPayload(null);
          }}
        >
          <option value="">Selecione</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <form
        className="record-form"
        key={student}
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget),
            body = {
              student_id: student,
              receivable_ids: f.getAll("receivables"),
              installments: Number(f.get("installments")),
              first_due: f.get("due"),
            };
          setBusy(true);
          setError("");
          try {
            setQuote(
              await api<Quote>(base + "/negotiations/simulate", {
                method: "POST",
                body: JSON.stringify(body),
              }),
            );
            setPayload(body);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <fieldset>
          <legend>Contas pendentes para incluir na proposta</legend>
          {sources
            .filter((r) => r.student_id === student && r.status === "pending")
            .map((r) => (
              <label className="checkbox-field" key={r.id}>
                <input type="checkbox" name="receivables" value={r.id} />
                {r.title} · {money(Number(r.data.amount_cents))} ·{" "}
                {r.data.due_date.split("-").reverse().join("/")}
              </label>
            ))}
        </fieldset>
        <label className="field">
          Quantidade de parcelas
          <input
            type="number"
            name="installments"
            min={1}
            max={24}
            defaultValue={3}
            required
          />
        </label>
        <label className="field">
          Primeiro vencimento
          <input name="due" type="date" required />
        </label>
        <Button disabled={busy || !student}>Calcular proposta</Button>
      </form>
      {quote && (
        <>
          <h3>Total {money(quote.total_cents)} · Sem juros</h3>
          <ScheduleTable schedule={quote.schedule} />
          <form
            className="record-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              setBusy(true);
              try {
                const result = await api<{ message: string }>(
                  base + "/negotiations/propose",
                  {
                    method: "POST",
                    body: JSON.stringify({
                      ...(payload as object),
                      note: f.get("note"),
                    }),
                  },
                );
                setMessage(result.message);
                setQuote(null);
                setPayload(null);
                await onSaved();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label className="field">
              Mensagem para análise da escola
              <textarea name="note" minLength={3} maxLength={2000} required />
            </label>
            <Button disabled={busy}>Enviar proposta para análise</Button>
          </form>
        </>
      )}
    </section>
  );
}
export function ScheduleTable({ schedule }: { schedule: ProposalSchedule[] }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Parcela</th>
            <th>Vencimento</th>
            <th>Valor</th>
          </tr>
        </thead>
        <tbody>
          {schedule.map((p) => (
            <tr key={p.number}>
              <td>{p.number}</td>
              <td>{p.due_date.split("-").reverse().join("/")}</td>
              <td>{money(p.amount_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
