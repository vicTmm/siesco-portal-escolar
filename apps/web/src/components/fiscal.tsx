"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { Button } from "./ui/button";
type Profile = Record<string, string | number | boolean> & {
  version: number;
  environment: string;
  next_number: number;
};
type Invoice = {
  id: string;
  version: number;
  student: string;
  guardian: string;
  environment: string;
  series: number;
  number: number;
  status: string;
  message: string;
  access_key: string | null;
  official_number: string | null;
  request: { description: string; competence: string; amount_cents: number };
};
const statuses: Record<string, string> = {
  draft: "Rascunho",
  submitting: "Aguardando confirmação",
  unknown: "Resultado a confirmar",
  authorized: "Autorizada",
  rejected: "Rejeitada",
};
const money = (cents: number) =>
  (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export function FiscalView({ base, role }: { base: string; role: string }) {
  const [profile, setProfile] = useState<Profile | null>(null),
    [loaded, setLoaded] = useState(false),
    [students, setStudents] = useState<Row[]>([]),
    [student, setStudent] = useState(""),
    [guardians, setGuardians] = useState<Row[]>([]),
    [items, setItems] = useState<Invoice[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [key, setKey] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Profile | null>(base + "/fiscal/profile"),
      allRows<Row>(base + "/students"),
      allRows<Invoice>(base + "/fiscal/invoices"),
    ])
      .then(([p, s, i]) => {
        if (active) {
          setProfile(p);
          setStudents(s);
          setItems(i);
          setKey(crypto.randomUUID());
          setLoaded(true);
        }
      })
      .catch((e) => setError(e.message));
    return () => {
      active = false;
    };
  }, [base]);
  useEffect(() => {
    let active = true;
    setGuardians([]);
    if (student)
      api<Row[]>(base + "/fiscal/guardians/" + student)
        .then((g) => {
          if (active) setGuardians(g);
        })
        .catch((e) => setError(e.message));
    return () => {
      active = false;
    };
  }, [base, student]);
  async function saveProfile(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    const f = new FormData(e.currentTarget);
    const numeric = [
      "series",
      "next_number",
      "simple_national",
      "simple_apportionment",
      "special_regime",
    ];
    const data = Object.fromEntries(
      [...f.entries()]
        .filter(([k]) => k !== "accounting_confirmed")
        .map(([k, v]) => [k, numeric.includes(k) ? Number(v) : v]),
    );
    try {
      const p = await api<Profile>(base + "/fiscal/profile", {
        method: "PUT",
        body: JSON.stringify({
          ...data,
          version: profile?.version || 0,
          accounting_confirmed: f.get("accounting_confirmed") === "on",
        }),
      });
      setProfile(p);
      setMessage(
        "Cadastro fiscal salvo. O certificado e a homologação são configurados de forma segura na instalação.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function draft(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      f = new FormData(form);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const raw = String(f.get("amount"));
      if (!/^\d+(?:[.,]\d{1,2})?$/.test(raw))
        throw new Error(
          "Informe o valor em reais com até duas casas decimais, sem separador de milhares.",
        );
      const [whole, fraction = ""] = raw.replace(",", ".").split(".");
      const amount = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
      const data = Object.fromEntries(
        [...f.entries()].filter(([k]) => k !== "amount"),
      );
      const r = await api<Invoice>(base + "/fiscal/invoices", {
        method: "POST",
        body: JSON.stringify({
          ...data,
          key,
          profile_version: profile!.version,
          student_id: student,
          amount_cents: amount,
        }),
      });
      setItems((old) => [r, ...old.filter((i) => i.id !== r.id)]);
      setKey(crypto.randomUUID());
      form.reset();
      setMessage(
        "Rascunho fiscal preparado. Confira os dados antes de enviar para emissão.",
      );
      const updated = await api<Profile>(base + "/fiscal/profile");
      setProfile(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function send(i: Invoice, operation: "emit" | "reconcile") {
    if (
      operation === "emit" &&
      !window.confirm(
        i.environment === "production"
          ? "Emitir uma NFS-e real para este tomador e valor?"
          : "Enviar a DPS ao ambiente de homologação, sem validade fiscal?",
      )
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const r = await api<Invoice>(
        base + `/fiscal/invoices/${i.id}/${operation}`,
        { method: "POST", body: JSON.stringify({ version: i.version }) },
      );
      setItems((old) => old.map((x) => (x.id === r.id ? r : x)));
      setMessage(r.message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const field = (
    name: string,
    label: string,
    type = "text",
    required = true,
    props: Record<string, string | number> = {},
  ) => (
    <label className="field" key={name}>
      {label}
      <input
        name={name}
        aria-label={label}
        type={type}
        defaultValue={String(profile?.[name] ?? "")}
        required={required}
        {...props}
      />
    </label>
  );
  const select = (
    name: string,
    label: string,
    options: [string, string][],
    fallback = "",
  ) => (
    <label className="field">
      {label}
      <select
        name={name}
        aria-label={label}
        defaultValue={String(profile?.[name] ?? fallback)}
        required
      >
        <option value="">Selecione</option>
        {options.map(([k, v]) => (
          <option key={k} value={k}>
            {v}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Notas fiscais de serviços</h1>
          <p>
            Prepare os dados, envie a DPS e acompanhe a autorização da NFS-e
            Nacional. Cobranças de mensalidades continuam no Isaac.
          </p>
        </div>
        <Button
          variant="outline"
          disabled={busy}
          onClick={async () => {
            try {
              const [invoices, updated] = await Promise.all([
                allRows<Invoice>(base + "/fiscal/invoices"),
                api<Profile | null>(base + "/fiscal/profile"),
              ]);
              setItems(invoices);
              setProfile(updated);
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Atualizar notas
        </Button>
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
      {!loaded && !error && <p role="status">Carregando cadastro fiscal…</p>}
      {loaded && (
        <section className="panel record-form">
          <h2>
            {profile
              ? `${profile.legal_name} · ${profile.environment === "test" ? "Homologação, sem validade fiscal" : "Produção"}`
              : "Cadastro fiscal pendente"}
          </h2>
          <p>
            O fluxo inicial atende ME/EPP optante pelo Simples Nacional, com
            serviços nacionais tributáveis, sem retenções, deduções ou regime
            especial. O contador deve confirmar os códigos e o enquadramento. O
            envio depende do certificado digital vinculado ao CNPJ da escola.
          </p>
          {role === "director" && (
            <details open={!profile}>
              <summary>Configurar dados fiscais da escola</summary>
              <form
                className="record-form"
                key={profile?.version || 0}
                onSubmit={saveProfile}
              >
                {field("cnpj", "CNPJ da escola", "text", true, {
                  pattern: "[0-9]{14}",
                  maxLength: 14,
                })}
                {field("legal_name", "Razão social", "text", true, {
                  maxLength: 150,
                })}
                {field(
                  "municipality_code",
                  "Código IBGE do município emissor",
                  "text",
                  true,
                  {
                    pattern: "[0-9]{7}",
                    placeholder: "3304904 — São Gonçalo/RJ",
                  },
                )}
                {field(
                  "municipal_registration",
                  "Inscrição municipal (se exigida)",
                  "text",
                  false,
                  { maxLength: 15 },
                )}
                {select(
                  "environment",
                  "Ambiente",
                  [
                    ["test", "Homologação — sem validade fiscal"],
                    ["production", "Produção — notas reais"],
                  ],
                  "test",
                )}
                {field("series", "Série da DPS", "number", true, {
                  min: 1,
                  max: 49999,
                })}
                {field("next_number", "Próximo número da DPS", "number", true, {
                  min: 1,
                  max: 999999999999999,
                })}
                {field(
                  "service_code",
                  "Código nacional do serviço (6 dígitos)",
                  "text",
                  true,
                  { pattern: "[0-9]{6}" },
                )}
                {field(
                  "municipal_service_code",
                  "Código municipal do serviço (opcional)",
                  "text",
                  false,
                  { pattern: "[0-9]{3}" },
                )}
                {field("nbs_code", "Código NBS (se exigido)", "text", false, {
                  pattern: "[0-9]{9}",
                })}
                {select("simple_national", "Opção pelo Simples Nacional", [
                  ["3", "Optante — ME/EPP"],
                ])}
                {select(
                  "simple_apportionment",
                  "Apuração do Simples",
                  [["1", "Tributos federais e ISS no Simples Nacional"]],
                  "1",
                )}
                {select("special_regime", "Regime especial", [
                  ["0", "Nenhum — confirmar com o contador"],
                ])}
                {field(
                  "total_tax_percent",
                  "Percentual total aproximado no Simples (%)",
                  "number",
                  true,
                  { min: 0, max: 99.99, step: "0.01" },
                )}
                <label className="checkbox-field">
                  <input type="checkbox" name="accounting_confirmed" required />
                  Confirmei com o contador o enquadramento e a compatibilidade
                  desta operação, sem retenções ou deduções.
                </label>
                <Button disabled={busy}>Salvar cadastro fiscal</Button>
              </form>
            </details>
          )}
          {!profile && role !== "director" && (
            <p>A direção deve concluir o cadastro fiscal.</p>
          )}
        </section>
      )}
      {profile && (
        <section className="panel record-form">
          <h2>Preparar NFS-e</h2>
          <label className="field">
            Aluno
            <select
              aria-label="Aluno da nota fiscal"
              value={student}
              disabled={busy}
              onChange={(e) => setStudent(e.target.value)}
            >
              <option value="">Selecione</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          {student && (
            <form className="record-form" key={student} onSubmit={draft}>
              <label className="field">
                Tomador — responsável verificado
                <select
                  name="guardian_id"
                  aria-label="Tomador — responsável verificado"
                  required
                >
                  {!guardians.length && (
                    <option value="">Nenhum responsável verificado</option>
                  )}
                  {guardians.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                CPF/CNPJ do tomador
                <input
                  name="tax_id"
                  aria-label="CPF/CNPJ do tomador"
                  required
                  pattern="(?:[0-9]{11}|[0-9]{14})"
                  maxLength={14}
                />
              </label>
              <label className="field">
                Competência
                <input
                  name="competence"
                  aria-label="Competência"
                  type="date"
                  max={new Date().toISOString().slice(0, 10)}
                  required
                />
              </label>
              <label className="field">
                Valor do serviço (R$)
                <input
                  name="amount"
                  aria-label="Valor do serviço (R$)"
                  inputMode="decimal"
                  placeholder="650,00"
                  required
                />
              </label>
              <label className="field">
                Descrição do serviço
                <textarea
                  name="description"
                  aria-label="Descrição do serviço"
                  required
                  minLength={5}
                  maxLength={2000}
                />
              </label>
              {[
                ["postal_code", "CEP do tomador", "[0-9]{8}"],
                [
                  "municipality_code",
                  "Código IBGE do município do tomador",
                  "[0-9]{7}",
                ],
                ["street", "Logradouro do tomador", ""],
                ["street_number", "Número do endereço", ""],
                ["district", "Bairro do tomador", ""],
              ].map(([name, label, pattern]) => (
                <label className="field" key={name}>
                  {label}
                  <input
                    name={name}
                    aria-label={label}
                    pattern={pattern || undefined}
                    maxLength={name === "street" ? 255 : 60}
                    required
                  />
                </label>
              ))}
              <Button disabled={busy || !guardians.length}>
                Preparar rascunho fiscal
              </Button>
            </form>
          )}
        </section>
      )}
      <section className="panel record-form">
        <h2>Notas e rascunhos</h2>
        {!items.length && loaded && <p>Nenhuma nota preparada.</p>}
        {items.map((i) => (
          <article className="learning-record" key={i.id}>
            <div>
              <h3>
                {i.official_number ? `NFS-e nº ${i.official_number} · ` : ""}
                {i.guardian}
              </h3>
              <p>
                {i.student} · {i.request.competence} ·{" "}
                {money(i.request.amount_cents)}
              </p>
              <p>{i.request.description}</p>
              <span className="badge green">
                {statuses[i.status]} ·{" "}
                {i.environment === "test"
                  ? "Homologação — sem validade fiscal"
                  : "Produção"}
              </span>
              <p>
                DPS: série {i.series}, número {i.number}
              </p>
              <p>{i.message}</p>
              {i.access_key && (
                <p className="preserve-lines">Chave: {i.access_key}</p>
              )}
              <div className="learning-toolbar">
                {i.status === "draft" && (
                  <Button disabled={busy} onClick={() => send(i, "emit")}>
                    {i.environment === "test"
                      ? "Emitir em homologação"
                      : "Emitir NFS-e"}
                  </Button>
                )}
                {["unknown", "submitting"].includes(i.status) && (
                  <Button disabled={busy} onClick={() => send(i, "reconcile")}>
                    Consultar retorno oficial
                  </Button>
                )}
                {i.status === "authorized" && (
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={async () => {
                      try {
                        const r = await api<{
                          filename: string;
                          base64: string;
                        }>(base + `/fiscal/invoices/${i.id}/xml`);
                        const bytes = Uint8Array.from(atob(r.base64), (c) =>
                          c.charCodeAt(0),
                        );
                        const url = URL.createObjectURL(
                          new Blob([bytes], { type: "application/xml" }),
                        );
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = r.filename;
                        a.click();
                        setTimeout(() => URL.revokeObjectURL(url), 1000);
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  >
                    Baixar XML autorizado
                  </Button>
                )}
              </div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
