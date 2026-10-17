"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
type Info = {
  signature?: string;
  title: string;
  institution: string;
  issued_at: string;
  valid: boolean;
  sha256: string;
};
export function Verification({ token }: { token: string }) {
  const [info, setInfo] = useState<Info | null>(null),
    [error, setError] = useState(""),
    [result, setResult] = useState("");
  useEffect(() => {
    api<Info>("verify-document/" + encodeURIComponent(token))
      .then(setInfo)
      .catch((e) => setError(e.message));
  }, [token]);
  return (
    <main className="main-content school-workflow">
      <section className="panel learning-body">
        <h1>Verificação de documento</h1>
        {error && <p role="alert">{error}</p>}
        {!info && !error && <p>Consultando registro…</p>}
        {info && (
          <>
            <h2>{info.title}</h2>
            <p>
              {info.institution} ·{" "}
              {new Date(info.issued_at).toLocaleString("pt-BR")}
            </p>
            <strong>
              {info.valid ? "Registro válido" : "Documento revogado"}
            </strong>
            {info.signature==="unsigned"&&<p>Minuta sem assinatura digital.</p>}
            <p>
              Selecione o PDF recebido para conferir se corresponde ao arquivo
              emitido. A comparação é feita neste dispositivo.
            </p>
            <label className="field">
              Conferir arquivo PDF
              <input
                type="file"
                accept="application/pdf"
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  const hash = await crypto.subtle.digest(
                    "SHA-256",
                    await f.arrayBuffer(),
                  );
                  const hex = Array.from(new Uint8Array(hash), (b) =>
                    b.toString(16).padStart(2, "0"),
                  ).join("");
                  setResult(
                    hex === info.sha256
                      ? "Arquivo corresponde ao documento emitido."
                      : "Arquivo diferente do documento emitido.",
                  );
                }}
              />
            </label>
            <p role="status">{result}</p>
            <p>A consulta confirma o registro e a integridade do documento.</p>
          </>
        )}
      </section>
    </main>
  );
}
