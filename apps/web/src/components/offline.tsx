"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  ApiError,
  allRows,
  selectMembership,
  type User,
  type Row,
} from "@/lib/api";
import {
  readOffline,
  saveOffline,
  removeOffline,
  offlineIdentity,
  clearOffline,
} from "@/lib/offline-store";
import { Button } from "./ui/button";
type Entry = { student_id: string; status: string };
type Lesson = {
  id: string;
  date: string;
  slot: number;
  content: string;
  cancelled: boolean;
  students: string[];
  attendance: Entry[];
};
type Journal = {
  term_start: string;
  term_end: string;
  placements: { student_id: string; start: string; end: string | null }[];
  id: string;
  version: number;
  status: string;
  students: { id: string; name: string }[];
  lessons: Lesson[];
};
type Prepared = {
  archives?: {
    saved_at: string;
    students: Journal["students"];
    drafts: Prepared["drafts"];
    changes: Prepared["changes"];
  }[];
  id: string;
  membership: string;
  base: string;
  name: string;
  journal: Journal;
  key: string;
  drafts: { date: string; slot: number; content: string; entries: Entry[] }[];
  changes: Record<string, Entry[]>;
};
export function OfflineView() {
  const [locked, setLocked] = useState(false);
  const [review, setReview] = useState<Journal | null>(null);
  const [lessonDate, setLessonDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [online, setOnline] = useState(true),
    [items, setItems] = useState<Prepared[]>([]),
    [journals, setJournals] = useState<Row[]>([]),
    [current, setCurrent] = useState<User["memberships"][number] | null>(null),
    [members, setMembers] = useState<User["memberships"]>([]),
    [selected, setSelected] = useState(""),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [lesson, setLesson] = useState("new");
  const item = items.find((i) => i.id === selected),
    eligible = items.filter((i) => !current || i.membership === current.id);
  async function stored() {
    setItems(await readOffline<Prepared>());
  }
  async function connect() {
    const user = await api<User>("me");
    const choices = user.memberships.filter((m) =>
      ["director", "coordinator", "teacher"].includes(m.role),
    );
    setMembers(choices);
    const chosen =
      choices.find(
        (m) => m.id === sessionStorage.getItem("siesco_offline_membership"),
      ) || choices[0];
    if (!chosen) {
      if (sessionStorage.getItem("siesco_offline_user") === user.id) {
        for (const old of await readOffline<Prepared>())
          await removeOffline(old.id);
      }
      throw new ApiError(403, "Seu perfil não permite editar diários offline.");
    }
    await offlineIdentity(user.id, chosen.id);
    const valid = new Set(choices.map((m) => m.id));
    for (const previous of await readOffline<Prepared>())
      if (!valid.has(previous.membership)) await removeOffline(previous.id);
    selectMembership(chosen.id);
    setCurrent(chosen);
    setJournals(
      await allRows<Row>(`institutions/${chosen.institution_id}/journals`),
    );
    sessionStorage.removeItem("siesco_offline_lock");
    setLocked(false);
    await stored();
  }
  useEffect(() => {
    const update = async () => {
      setOnline(navigator.onLine);
      if (!navigator.onLine) {
        if (sessionStorage.getItem("siesco_offline_lock")) {
          setLocked(true);
          return;
        }
        await stored();
        return;
      }
      try {
        await connect();
        for (const prepared of await readOffline<Prepared>()) {
          if (prepared.drafts.length || Object.keys(prepared.changes).length)
            await synchronize(prepared);
        }
      } catch (e) {
        const failure = e as ApiError;
        setError(failure.message);
        if ([401, 403, 404].includes(failure.status)) {
          sessionStorage.setItem("siesco_offline_lock", "1");
          setLocked(true);
          setItems(await readOffline<Prepared>().catch(() => []));
        } else await stored();
      }
    };
    void update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  async function persist(updated: Prepared) {
    await saveOffline(updated.id, updated);
    await stored();
  }
  async function prepare(id: string) {
    if (!current) return;
    setBusy(true);
    setError("");
    try {
      const base = `institutions/${current.institution_id}`,
        j = await api<Journal>(base + "/journals/" + id + "/offline-package");
      if (j.status !== "draft")
        throw new Error("Prepare apenas diários abertos.");
      const existing = items.find((i) => i.id === current.id + "/" + id);
      if (
        existing &&
        (existing.drafts.length || Object.keys(existing.changes).length)
      )
        throw new Error(
          "Sincronize ou descarte os rascunhos antes de atualizar este diário.",
        );
      const prepared = {
        id: current.id + "/" + id,
        membership: current.id,
        base,
        name: String(journals.find((i) => i.id === id)?.name || "Diário"),
        journal: j,
        key: crypto.randomUUID(),
        drafts: [],
        changes: {},
      };
      await persist(prepared);
      setSelected(prepared.id);
      setLessonDate(
        new Date().toISOString().slice(0, 10) < j.term_start
          ? j.term_start
          : new Date().toISOString().slice(0, 10) > j.term_end
            ? j.term_end
            : new Date().toISOString().slice(0, 10),
      );
      setMessage(
        "Diário preparado neste dispositivo. Você pode registrar rascunhos sem conexão.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function synchronize(i: Prepared) {
    setBusy(true);
    setError("");
    try {
      selectMembership(i.membership);
      await api(i.base + `/journals/${i.journal.id}/offline-sync`, {
        method: "POST",
        body: JSON.stringify({
          key: i.key,
          version: i.journal.version,
          lessons: i.drafts,
          attendance: Object.entries(i.changes).map(([lesson_id, entries]) => ({
            lesson_id,
            entries,
          })),
        }),
      });
      const fresh = await api<Journal>(
        i.base + `/journals/${i.journal.id}/offline-package`,
      );
      await persist({
        ...i,
        journal: fresh,
        key: crypto.randomUUID(),
        drafts: [],
        changes: {},
      });
      setMessage(
        "Rascunhos sincronizados. O servidor validou permissões, versão e matrículas.",
      );
    } catch (e) {
      if ((e as ApiError).status === 404) {
        await removeOffline(i.id);
        await stored();
        setSelected("");
        setError(
          "O diário ou o acesso não está mais disponível. A cópia local foi removida.",
        );
        return;
      }
      if ([401, 403].includes((e as ApiError).status)) {
        sessionStorage.setItem("siesco_offline_lock", "1");
        setLocked(true);
        setError(
          "Entre novamente e revalide o acesso para sincronizar. Os rascunhos foram preservados.",
        );
        return;
      }
      setError(
        (e as Error).message +
          " Os rascunhos continuam neste dispositivo para revisão.",
      );
    } finally {
      selectMembership(
        sessionStorage.getItem("siesco_offline_membership") || "",
      );
      setBusy(false);
    }
  }
  if (locked)
    return (
      <section className="school-workflow panel">
        <h1>Revalidar acesso ao diário offline</h1>
        <p>
          Entre novamente no portal e abra esta página com conexão.
          {items.length
            ? " Seus rascunhos foram preservados; a sincronização exige acesso autorizado pela escola."
            : " Nenhum diário preparado."}
        </p>
        <Link href="/">Entrar no portal</Link>
      </section>
    );
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Diário offline</h1>
          <p>
            {online ? "Conectado" : "Sem conexão"} · Prepare um diário antes de
            sair da rede.
          </p>
        </div>
        <Link href="/">Voltar ao portal</Link>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <p>
        Os rascunhos ficam cifrados neste navegador. Sair da conta ou limpar os
        dados locais remove as cópias. A sincronização exige conexão e acesso
        vigente; alterações concorrentes precisam de revisão.
      </p>
      {online && (
        <section className="panel record-form">
          <label className="field">
            Unidade e perfil
            <select
              aria-label="Unidade e perfil"
              value={current?.id || ""}
              onChange={async (e) => {
                const m = members.find((m) => m.id === e.target.value)!;
                selectMembership(m.id);
                setCurrent(m);
                sessionStorage.setItem("siesco_offline_membership", m.id);
                setSelected("");
                setReview(null);
                try {
                  setJournals(
                    await allRows(`institutions/${m.institution_id}/journals`),
                  );
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.school_name} · {m.role}
                </option>
              ))}
            </select>
          </label>
          <h2>Preparar para uso sem conexão</h2>
          {journals
            .filter((j) => j.status === "draft")
            .map((j) => (
              <Button
                variant="outline"
                disabled={busy}
                key={j.id}
                onClick={() => prepare(j.id)}
              >
                {String(j.name)} · {j.term}
              </Button>
            ))}
        </section>
      )}
      <section className="panel record-form">
        <h2>Diários deste dispositivo</h2>
        <label className="field">
          Diário preparado
          <select
            aria-label="Diário preparado"
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              setReview(null);
              setLesson("new");
            }}
          >
            <option value="">Selecione</option>
            {eligible.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name} · {i.drafts.length + Object.keys(i.changes).length}{" "}
                rascunhos
              </option>
            ))}
          </select>
        </label>
        {!items.length && <p>Nenhum diário preparado.</p>}
        {item && (
          <>
            <p>Versão preparada: {item.journal.version}</p>
            <label className="field">
              Aula
              <select
                aria-label="Aula"
                value={lesson}
                onChange={(e) => setLesson(e.target.value)}
              >
                <option value="new">Nova aula e chamada</option>
                {item.journal.lessons
                  .filter((l) => !l.cancelled)
                  .map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.date} · Aula {l.slot} · {l.content}
                    </option>
                  ))}
              </select>
            </label>
            <form
              className="record-form"
              key={item.id + lesson}
              onSubmit={async (e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const existing = item.journal.lessons.find(
                    (l) => l.id === lesson,
                  ),
                  students = existing
                    ? item.journal.students.filter((s) =>
                        existing.students.includes(s.id),
                      )
                    : item.journal.students.filter((s) =>
                        item.journal.placements.some(
                          (p) =>
                            p.student_id === s.id &&
                            p.start <= lessonDate &&
                            (!p.end || p.end > lessonDate),
                        ),
                      );
                const entries = students.map((s) => ({
                  student_id: s.id,
                  status: String(f.get(s.id)),
                }));
                try {
                  if (existing)
                    await persist({
                      ...item,
                      key: crypto.randomUUID(),
                      changes: { ...item.changes, [lesson]: entries },
                    });
                  else
                    await persist({
                      ...item,
                      key: crypto.randomUUID(),
                      drafts: [
                        ...item.drafts,
                        {
                          date: String(f.get("date")),
                          slot: Number(f.get("slot")),
                          content: String(f.get("content")),
                          entries,
                        },
                      ],
                    });
                  setMessage("Rascunho guardado no dispositivo.");
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              {lesson === "new" && (
                <>
                  <label className="field">
                    Data
                    <input
                      name="date"
                      type="date"
                      value={lessonDate}
                      min={item.journal.term_start}
                      max={item.journal.term_end}
                      onChange={(e) => setLessonDate(e.target.value)}
                      required
                    />
                  </label>
                  <label className="field">
                    Aula do dia
                    <input
                      name="slot"
                      type="number"
                      min={1}
                      max={12}
                      defaultValue={1}
                      required
                    />
                  </label>
                  <label className="field">
                    Conteúdo / plano de aula
                    <textarea
                      name="content"
                      minLength={2}
                      maxLength={2000}
                      required
                    />
                  </label>
                </>
              )}
              {item.journal.students
                .filter(
                  (s) =>
                    (lesson === "new" &&
                      item.journal.placements.some(
                        (p) =>
                          p.student_id === s.id &&
                          p.start <= lessonDate &&
                          (!p.end || p.end > lessonDate),
                      )) ||
                    item.journal.lessons
                      .find((l) => l.id === lesson)
                      ?.students.includes(s.id),
                )
                .map((s) => {
                  const previous =
                    (
                      item.changes[lesson] ||
                      item.journal.lessons.find((l) => l.id === lesson)
                        ?.attendance ||
                      []
                    ).find((a) => a.student_id === s.id)?.status || "";
                  return (
                    <label className="field" key={s.id}>
                      {s.name}
                      <select
                        aria-label={s.name}
                        name={s.id}
                        required
                        defaultValue={previous}
                      >
                        <option value="">Selecione a frequência</option>
                        <option value="present">Presente</option>
                        <option value="absent">Falta</option>
                        <option value="excused">Justificada</option>
                      </select>
                    </label>
                  );
                })}
              <Button disabled={busy}>Guardar rascunho local</Button>
            </form>
            <p>
              {item.drafts.length} novas aulas e{" "}
              {Object.keys(item.changes).length} chamadas alteradas.
            </p>
            <Button
              disabled={
                busy ||
                !online ||
                (!item.drafts.length && !Object.keys(item.changes).length)
              }
              onClick={() => synchronize(item)}
            >
              Sincronizar rascunhos
            </Button>
            <details>
              <summary>Revisar rascunhos antes de descartar</summary>
              {item.drafts.map((d, i) => (
                <div key={i}>
                  <h3>
                    {d.date} · Aula {d.slot}
                  </h3>
                  <p>{d.content}</p>
                  {d.entries.map((e) => (
                    <p key={e.student_id}>
                      {
                        item.journal.students.find((s) => s.id === e.student_id)
                          ?.name
                      }
                      : {e.status}
                    </p>
                  ))}
                </div>
              ))}
              {Object.entries(item.changes).map(([id, entries]) => (
                <div key={id}>
                  <h3>
                    {item.journal.lessons.find((l) => l.id === id)?.content}
                  </h3>
                  {entries.map((e) => (
                    <p key={e.student_id}>
                      {
                        item.journal.students.find((s) => s.id === e.student_id)
                          ?.name
                      }
                      : {e.status}
                    </p>
                  ))}
                </div>
              ))}
            </details>
            {online && (
              <Button
                variant="outline"
                disabled={busy}
                onClick={async () => {
                  try {
                    selectMembership(item.membership);
                    setReview(
                      await api<Journal>(
                        item.base +
                          `/journals/${item.journal.id}/offline-package`,
                      ),
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Revisar versão atual e conflitos
              </Button>
            )}
            {review && review.id === item.journal.id && (
              <ConflictReview
                item={item}
                current={review}
                busy={busy}
                onClose={() => setReview(null)}
                onApply={async (updated) => {
                  try {
                    await persist(updated);
                    setReview(null);
                    if (
                      updated.drafts.length ||
                      Object.keys(updated.changes).length
                    )
                      await synchronize(updated);
                    else
                      setMessage(
                        "Revisão arquivada no dispositivo. Nenhuma alteração enviada.",
                      );
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              />
            )}
            {!!item.archives?.length && (
              <details>
                <summary>
                  Histórico local de revisão ({item.archives.length})
                </summary>
                {item.archives.map((a, n) => (
                  <div key={n}>
                    <small>
                      {new Date(a.saved_at).toLocaleString("pt-BR")}
                    </small>
                    {a.drafts.map((d, k) => (
                      <p key={k}>
                        {d.date} · Aula {d.slot} · {d.content}
                      </p>
                    ))}
                    {Object.entries(a.changes).map(([id, entries]) => (
                      <div key={id}>
                        {entries.map((entry) => (
                          <p key={entry.student_id}>
                            {a.students.find((s) => s.id === entry.student_id)
                              ?.name || "Aluno da revisão"}
                            : {entry.status}
                          </p>
                        ))}
                      </div>
                    ))}
                  </div>
                ))}
              </details>
            )}
            <Button
              variant="outline"
              onClick={async () => {
                await removeOffline(item.id);
                await stored();
                setSelected("");
              }}
            >
              Descartar cópia local deste diário
            </Button>
          </>
        )}
      </section>
      <Button
        variant="outline"
        onClick={async () => {
          await clearOffline();
          setItems([]);
          setSelected("");
          setMessage(
            "Cópias locais removidas. Entre novamente para preparar outro diário.",
          );
        }}
      >
        Limpar todos os dados offline
      </Button>
    </div>
  );
}
function ConflictReview({
  item,
  current,
  busy,
  onApply,
  onClose,
}: {
  item: Prepared;
  current: Journal;
  busy: boolean;
  onApply: (updated: Prepared) => Promise<void>;
  onClose: () => void;
}) {
  const status = (value?: string) =>
    ({ present: "Presente", absent: "Falta", excused: "Justificada" })[
      value || ""
    ] || "Pendente";
  const eligible = (entry: Entry, day: string) =>
    current.placements.some(
      (p) =>
        p.student_id === entry.student_id &&
        p.start <= day &&
        (!p.end || p.end > day),
    );
  return (
    <section className="panel record-form">
      <h3>Revisão do diário</h3>
      <p>
        Versão local: {item.journal.version} · Versão no servidor:{" "}
        {current.version}. Selecione os trechos que deseja reaplicar. A revisão
        original fica no histórico deste dispositivo.
      </p>
      {current.status !== "draft" && (
        <p>
          O diário está fechado. Solicite reabertura antes de sincronizar
          alterações.
        </p>
      )}
      <form
        className="record-form"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget),
            drafts = item.drafts
              .filter((_, n) => f.has("draft_" + n))
              .map((d) => ({
                ...d,
                entries: d.entries.filter((entry) => eligible(entry, d.date)),
              })),
            changes: Record<string, Entry[]> = {};
          for (const [id, entries] of Object.entries(item.changes)) {
            const chosen = entries.filter((entry) =>
              f.has(id + "_" + entry.student_id),
            );
            if (chosen.length) changes[id] = chosen;
          }
          onApply({
            ...item,
            journal: current,
            key: crypto.randomUUID(),
            drafts,
            changes,
            archives: [
              ...(item.archives || []),
              {
                saved_at: new Date().toISOString(),
                students: item.journal.students,
                drafts: item.drafts,
                changes: item.changes,
              },
            ],
          });
        }}
      >
        {item.drafts.map((d, n) => {
          const duplicate = current.lessons.some(
              (l) => l.date === d.date && l.slot === d.slot,
            ),
            count = d.entries.filter((entry) => eligible(entry, d.date)).length;
          return (
            <label className="checkbox-field" key={n}>
              <input
                name={"draft_" + n}
                type="checkbox"
                disabled={duplicate || !count || current.status !== "draft"}
              />
              Reaplicar aula {d.date} · {d.slot}: {d.content} · {count} alunos
              elegíveis
              {duplicate
                ? " · Já existe uma aula neste horário no servidor."
                : ""}
            </label>
          );
        })}
        {Object.entries(item.changes).map(([id, entries]) => {
          const lesson = current.lessons.find(
            (l) => l.id === id && !l.cancelled,
          );
          return (
            <fieldset key={id}>
              <legend>{lesson?.content || "Aula indisponível"}</legend>
              {entries.map((entry) => (
                <label className="checkbox-field" key={entry.student_id}>
                  <input
                    name={id + "_" + entry.student_id}
                    type="checkbox"
                    disabled={
                      !lesson?.students.includes(entry.student_id) ||
                      current.status !== "draft"
                    }
                  />
                  {
                    item.journal.students.find((s) => s.id === entry.student_id)
                      ?.name
                  }{" "}
                  · Servidor:{" "}
                  {status(
                    lesson?.attendance.find(
                      (a) => a.student_id === entry.student_id,
                    )?.status,
                  )}{" "}
                  · Rascunho: {status(entry.status)}
                </label>
              ))}
            </fieldset>
          );
        })}
        <label className="checkbox-field">
          <input type="checkbox" required />
          Revisei as diferenças e confirmo a seleção.
        </label>
        <Button disabled={busy || current.status !== "draft"}>
          Concluir revisão e sincronizar seleção
        </Button>
        <Button variant="outline" type="button" onClick={onClose}>
          Voltar sem alterar
        </Button>
      </form>
    </section>
  );
}
