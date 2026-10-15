"use client";
import { useEffect, useRef, useState } from "react";
import { api, allRows, type Row } from "@/lib/api";
import { Attachments } from "./services";
import { Button } from "./ui/button";
type RecordItem = {
  id: string;
  student: string;
  student_id: string;
  status: string;
  version: number;
  data: Record<string, string>;
};
type Code = {
  code: string;
  qr_base64: string;
  expires_at: string;
  student?: string;
  school?: string;
};
type Location = { latitude: number; longitude: number; radius_m: number };
export function AccessControlView({
  base,
  role,
}: {
  base: string;
  role: string;
}) {
  const cardRequest = useRef(0);
  const staff = ["director", "secretary"].includes(role),
    guardian = role === "guardian",
    [students, setStudents] = useState<Row[]>([]),
    [student, setStudent] = useState(""),
    [card, setCard] = useState<Code | null>(null),
    [records, setRecords] = useState<RecordItem[]>([]),
    [queue, setQueue] = useState<RecordItem[]>([]),
    [consents, setConsents] = useState<
      {
        id: string;
        title: string;
        purpose: string;
        kind: string;
        archived: boolean;
      }[]
    >([]),
    [location, setLocation] = useState<Location | null>(null),
    [code, setCode] = useState<(Code & { record_id: string }) | null>(null),
    [attachment, setAttachment] = useState(""),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [board, setBoard] = useState(false),
    [release, setRelease] = useState<RecordItem | null>(null);
  async function load() {
    if (staff || guardian) {
      setRecords(await allRows<RecordItem>(base + "/pickups"));
      setQueue(await allRows<RecordItem>(base + "/pickup-queue"));
    }
  }
  async function refreshCard() {
    if (student) {
      const request = ++cardRequest.current;
      const result = await api<Code>(base + `/school-cards/${student}/issue`, {
          method: "POST",
        });
      if (request === cardRequest.current) setCard(result);
    }
  }
  useEffect(() => {
    (staff
      ? allRows(base + "/students")
      : api<{ students: Row[] }>(base + "/portal?limit=100").then(
          (d) => d.students,
        )
    )
      .then(setStudents)
      .catch((e) => setError(e.message));
    if (staff || guardian) {
      load().catch((e) => setError(e.message));
      api<Location | null>(base + "/pickup-location")
        .then(setLocation)
        .catch((e) => setError(e.message));
      allRows<{
        id: string;
        title: string;
        purpose: string;
        kind: string;
        archived: boolean;
      }>(base + "/notices")
        .then((n) =>
          setConsents(
            n.filter(
              (n) =>
                n.kind === "authorization" &&
                n.purpose === "pickup" &&
                !n.archived,
            ),
          ),
        )
        .catch((e) => setError(e.message));
      const timer = setInterval(
        () => load().catch((e) => setError(e.message)),
        5000,
      );
      return () => clearInterval(timer);
    }
  }, [base, staff, guardian]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    setCard(null);
    if (!student) return;
    refreshCard().catch((e) => setError(e.message));
    const timer = setInterval(
      () => refreshCard().catch((e) => setError(e.message)),
      60000,
    );
    return () => { clearInterval(timer); cardRequest.current++; };
  }, [base, student]); // eslint-disable-line react-hooks/exhaustive-deps
  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function arrive(form: HTMLFormElement, gps: boolean) {
    const f = new FormData(form);
    await run(async () => {
      const body: {
        student_id: string;
        vehicle: string;
        latitude?: number;
        longitude?: number;
        accuracy_m?: number;
      } = { student_id: student, vehicle: String(f.get("vehicle")) };
      if (gps) {
        const position = await new Promise<GeolocationPosition>(
          (resolve, reject) =>
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              enableHighAccuracy: true,
              timeout: 10000,
              maximumAge: 0,
            }),
        );
        if (position.coords.accuracy > 200)
          throw new Error(
            "A precisão da localização é insuficiente. Tente novamente ou sinalize a chegada manualmente.",
          );
        body.latitude = position.coords.latitude;
        body.longitude = position.coords.longitude;
        body.accuracy_m = position.coords.accuracy;
      }
      await api(base + "/pickup-queue", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setMessage(
        "Chegada sinalizada. Aguarde a chamada e a conferência da equipe.",
      );
    });
  }
  if (board && staff)
    return (
      <section className="school-workflow panel">
        <h1>Fila de saída</h1>
        <p>Chamadas da equipe</p>
        {queue
          .filter((q) => q.status === "called")
          .map((q) => (
            <div className="panel" key={q.id}>
              <h2>{q.student}</h2>
              <p>Dirija-se ao ponto de saída acompanhado pela equipe.</p>
            </div>
          ))}
        <Button variant="outline" onClick={() => setBoard(false)}>
          Voltar à portaria
        </Button>
      </section>
    );
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Identificação e saída</h1>
          <p>Identificação escolar, retirada por terceiro e fila de chegada.</p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <section className="panel record-form">
        <label className="field">
          Aluno
          <select
            aria-label="Aluno da identificação"
            value={student}
            onChange={(e) => { cardRequest.current++; setCard(null); setStudent(e.target.value); }}
          >
            <option value="">Selecione</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        {card && (
          <>
            <h2>{card.student}</h2>
            <p>{card.school}</p>
            <img
              width={240}
              height={240}
              src={"data:image/png;base64," + card.qr_base64}
              alt="QR Code temporário de identificação escolar"
            />
            <p>
              Identificação válida até{" "}
              {new Date(card.expires_at).toLocaleTimeString("pt-BR")}. Atualiza
              a cada minuto enquanto esta tela estiver aberta.
            </p>
            <p>
              Uso interno da escola; a equipe confere a identidade de quem
              apresenta o código.
            </p>
            <Button
              variant="outline"
              onClick={() => refreshCard().catch((e) => setError(e.message))}
            >
              Atualizar identificação
            </Button>
            <details>
              <summary>Copiar código para conferência</summary>
              <textarea
                readOnly
                value={card.code}
                aria-label="Código de identificação"
              />
            </details>
          </>
        )}
      </section>
      {staff && (
        <form
          className="panel record-form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(
                e.currentTarget,
                (e.nativeEvent as SubmitEvent).submitter,
              ),
              value = String(f.get("code")).trim();
            run(async () => {
              const result = await api<{
                message: string;
                student: string;
                person?: string;
              }>(
                base +
                  (value.startsWith("SIESCO:CARD:")
                    ? f.get("operation") === "entry"
                      ? "/school-cards/register-entry"
                      : "/school-cards/check"
                    : "/pickups/check"),
                {
                  method: "POST",
                  body: JSON.stringify({
                    code: value,
                    identity_verified: f.has("verified"),
                  }),
                },
              );
              setMessage(
                result.student +
                  (result.person ? " · " + result.person : "") +
                  " · " +
                  result.message,
              );
            });
          }}
        >
          <h2>Conferir código apresentado</h2>
          <label className="field">
            Código lido pelo scanner ou copiado da tela
            <textarea name="code" minLength={20} maxLength={4096} required />
          </label>
          <label>
            <input name="verified" type="checkbox" /> Conferi presencialmente a
            identidade, o documento e a autorização da pessoa que fará a
            retirada.
          </label>
          <Button name="operation" value="check" disabled={busy}>
            Conferir identificação / registrar retirada
          </Button>
          <Button
            name="operation"
            value="entry"
            variant="outline"
            disabled={busy}
          >
            Registrar entrada com identificação escolar
          </Button>
        </form>
      )}
      {guardian && (
        <form
          className="panel record-form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              await api(base + "/pickups", {
                method: "POST",
                body: JSON.stringify({
                  student_id: student,
                  person: f.get("person"),
                  relationship: f.get("relationship"),
                  valid_until: new Date(String(f.get("until"))).toISOString(),
                  consent_notice: f.get("consent"),
                }),
              });
              setMessage(
                "Pessoa autorizada registrada. Anexe o documento para gerar o código de uso único.",
              );
            });
          }}
        >
          <h2>Autorizar retirada por terceiro</h2>
          <p>
            Responda à autorização de retirada no mural antes de cadastrar a
            pessoa.
          </p>
          <label className="field">
            Pessoa autorizada
            <input name="person" minLength={3} maxLength={160} required />
          </label>
          <label className="field">
            Vínculo com o aluno
            <input name="relationship" minLength={2} maxLength={100} required />
          </label>
          <label className="field">
            Válido até (máximo de 24 horas)
            <input name="until" type="datetime-local" required />
          </label>
          <label className="field">
            Autorização publicada
            <select
              aria-label="Autorização de retirada"
              name="consent"
              required
            >
              <option value="">Selecione</option>
              {consents.map((c) => (
                <option value={c.id} key={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </label>
          <Button disabled={busy || !student}>
            Registrar pessoa autorizada
          </Button>
        </form>
      )}
      {(staff || guardian) && (
        <section className="panel">
          <h2>Retiradas autorizadas</h2>
          {records.map((r) => (
            <article className="learning-record" key={r.id}>
              <div>
                <h3>
                  {r.student} · {r.data.person}
                </h3>
                <p>
                  {r.data.relationship} · Até{" "}
                  {new Date(r.data.valid_until).toLocaleString("pt-BR")}
                </p>
                <p>
                  {r.status === "expected"
                    ? "Aguardando retirada"
                    : r.status === "released"
                      ? "Retirada registrada"
                      : "Cancelada"}
                </p>
                <div className="learning-toolbar">
                  <Button variant="outline" onClick={() => setAttachment(r.id)}>
                    Anexar / conferir documento
                  </Button>
                  {r.status === "expected" && (
                    <>
                      <Button
                        disabled={busy}
                        onClick={() =>
                          run(async () => {
                            setCode({
                              ...(await api<Code>(
                                base + `/pickups/${r.id}/code`,
                                { method: "POST" },
                              )),
                              record_id: r.id,
                            });
                          })
                        }
                      >
                        Gerar código de uso único
                      </Button>
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() =>
                          run(async () => {
                            await api(
                              base + `/service-records/${r.id}/transition`,
                              {
                                method: "POST",
                                body: JSON.stringify({
                                  version: r.version,
                                  status: "cancelled",
                                  note: "Retirada cancelada pelo usuário autorizado.",
                                }),
                              },
                            );
                            setCode(null);
                            setMessage("Retirada cancelada.");
                          })
                        }
                      >
                        Cancelar autorização de retirada
                      </Button>
                    </>
                  )}
                </div>
                {attachment === r.id && (
                  <Attachments
                    base={base}
                    record={r.id}
                    writable={guardian || staff}
                  />
                )}{" "}
                {code?.record_id === r.id && r.status === "expected" && (
                  <div>
                    <img
                      width={240}
                      height={240}
                      src={"data:image/png;base64," + code.qr_base64}
                      alt="QR Code de retirada de uso único"
                    />
                    <p>
                      Válido até{" "}
                      {new Date(code.expires_at).toLocaleString("pt-BR")}
                    </p>
                    <label className="field">
                      Código de retirada
                      <textarea readOnly value={code.code} />
                    </label>
                  </div>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
      {(staff || guardian) && (
        <>
          <form
            className="panel record-form"
            onSubmit={(e) => {
              e.preventDefault();
              arrive(e.currentTarget, false);
            }}
          >
            <h2>Sinalizar chegada</h2>
            <label className="field">
              Veículo / referência para a equipe
              <input name="vehicle" minLength={2} maxLength={100} required />
            </label>
            <Button disabled={busy || !student}>Já cheguei (manual)</Button>
            {location && (
              <Button
                type="button"
                variant="outline"
                disabled={busy || !student}
                onClick={(e) => {
                  const form = e.currentTarget.closest("form")!;
                  if (form.reportValidity()) arrive(form, true);
                }}
              >
                Sinalizar por localização (até {location.radius_m} m)
              </Button>
            )}
          </form>
          <section className="panel">
            <h2>Fila de chegada</h2>
            {staff && (
              <Button variant="outline" onClick={() => setBoard(true)}>
                Abrir painel de chamada
              </Button>
            )}
            {queue.map((q) => (
              <article className="learning-record" key={q.id}>
                <div>
                  <h3>{q.student}</h3>
                  <p>
                    {q.data.vehicle} ·{" "}
                    {q.data.method === "gps"
                      ? "Chegada informada por localização"
                      : "Chegada manual"}
                  </p>
                  <p>
                    {q.status === "called"
                      ? "Chamado pela equipe"
                      : "Aguardando chamada"}
                  </p>
                </div>
                <div>
                  {staff && q.status === "waiting" && (
                    <Button
                      disabled={busy}
                      onClick={() =>
                        run(async () => {
                          await api(
                            base + `/service-records/${q.id}/transition`,
                            {
                              method: "POST",
                              body: JSON.stringify({
                                version: q.version,
                                status: "called",
                                note: "Equipe chamou o aluno para a saída.",
                              }),
                            },
                          );
                        })
                      }
                    >
                      Chamar aluno
                    </Button>
                  )}
                  {staff && (
                    <Button variant="outline" onClick={() => setRelease(q)}>
                      Registrar saída após conferência
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        await api(
                          base + `/service-records/${q.id}/transition`,
                          {
                            method: "POST",
                            body: JSON.stringify({
                              version: q.version,
                              status: "cancelled",
                              note: "Chegada cancelada pelo usuário autorizado.",
                            }),
                          },
                        );
                      })
                    }
                  >
                    Cancelar chegada
                  </Button>
                </div>
              </article>
            ))}
            {release && (
              <form
                className="record-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  run(async () => {
                    await api(base + `/pickup-queue/${release.id}/release`, {
                      method: "POST",
                      body: JSON.stringify({
                        version: release.version,
                        identity_verified: f.has("verified"),
                        note: f.get("note"),
                      }),
                    });
                    setRelease(null);
                    setMessage("Saída registrada após conferência.");
                  });
                }}
              >
                <h3>Conferir saída de {release.student}</h3>
                <label>
                  <input type="checkbox" name="verified" required /> Conferi a
                  identidade e a autorização da pessoa presente.
                </label>
                <label className="field">
                  Confirmação / observação
                  <input name="note" minLength={3} maxLength={1000} required />
                </label>
                <Button disabled={busy}>Confirmar saída</Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setRelease(null)}
                >
                  Cancelar
                </Button>
              </form>
            )}
          </section>
        </>
      )}
      {staff && (
        <details className="panel">
          <summary>Configurar localização da escola</summary>
          <form
            className="record-form"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                const config = await api<Location>(base + "/pickup-location", {
                  method: "PUT",
                  body: JSON.stringify({
                    latitude: Number(f.get("latitude")),
                    longitude: Number(f.get("longitude")),
                    radius_m: Number(f.get("radius")),
                  }),
                });
                setLocation(config);
                setMessage("Localização atualizada.");
              });
            }}
          >
            <label className="field">
              Latitude
              <input
                name="latitude"
                type="number"
                min={-90}
                max={90}
                step="0.000001"
                required
                defaultValue={location?.latitude}
              />
            </label>
            <label className="field">
              Longitude
              <input
                name="longitude"
                type="number"
                min={-180}
                max={180}
                step="0.000001"
                required
                defaultValue={location?.longitude}
              />
            </label>
            <label className="field">
              Raio de chegada em metros
              <input
                name="radius"
                type="number"
                min={50}
                max={2000}
                defaultValue={location?.radius_m || 500}
                required
              />
            </label>
            <Button disabled={busy}>Salvar localização</Button>
          </form>
        </details>
      )}
    </div>
  );
}
