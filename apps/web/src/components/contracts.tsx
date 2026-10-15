"use client";
import { useEffect, useState } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { Button } from "./ui/button";
export function ContractDraftForm({
  base,
  students,
  onIssued,
}: {
  base: string;
  students: Row[];
  onIssued: () => Promise<void>;
}) {
  const [templates, setTemplates] = useState<
      { id: string; title: string; status: string }[]
    >([]),
    [guardians, setGuardians] = useState<Row[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    allRows<{ id: string; title: string; status: string }>(
      base + "/services/contract_templates",
    )
      .then((t) => setTemplates(t.filter((t) => t.status === "published")))
      .catch((e) => setError(e.message));
    allRows(base + "/guardians")
      .then(setGuardians)
      .catch((e) => setError(e.message));
  }, [base]);
  return (
    <details className="panel">
      <summary>Preparar minuta de contrato</summary>
      <p>
        Use o texto publicado pela direção. O PDF é uma minuta sem assinatura; a
        escola revisa os dados antes de encaminhar ao serviço de assinatura.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <form
        className="record-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setBusy(true);
          setError("");
          try {
            await api(base + "/contracts/draft", {
              method: "POST",
              body: JSON.stringify({
                template_id: f.get("template"),
                student_id: f.get("student"),
                guardian_id: f.get("guardian"),
                academic_year: Number(f.get("year")),
                monthly_cents: Math.round(Number(f.get("amount")) * 100),
              }),
            });
            await onIssued();
            setMessage(
              "Minuta preparada. O PDF está disponível na lista de documentos.",
            );
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label className="field">
          Modelo publicado
          <select aria-label="Modelo contratual" name="template" required>
            <option value="">Selecione</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Aluno da minuta
          <select aria-label="Aluno da minuta" name="student" required>
            <option value="">Selecione</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Responsável com vínculo verificado
          <select aria-label="Responsável da minuta" name="guardian" required>
            <option value="">Selecione</option>
            {guardians.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Ano letivo da minuta
          <input
            name="year"
            type="number"
            min={2000}
            max={2100}
            defaultValue={new Date().getFullYear()}
            required
          />
        </label>
        <label className="field">
          Mensalidade (R$)
          <input
            type="number"
            name="amount"
            min={0}
            max={10000000}
            step="0.01"
            required
          />
        </label>
        <Button disabled={busy}>Preparar PDF sem assinatura</Button>
      </form>
    </details>
  );
}
