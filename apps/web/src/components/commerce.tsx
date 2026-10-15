"use client";
import { useEffect, useState, useRef, type FormEvent } from "react";
import { api, allRows, ApiError, type Row } from "@/lib/api";
import { Button } from "./ui/button";
type Product = {
  id: string;
  channel: string;
  code: string;
  name: string;
  price_cents: number;
  stock: number;
  tags: string[];
  active: boolean;
  version: number;
};
type Statement = {
  student: string;
  balance_cents: number;
  policy: {
    version: number;
    daily_limit_cents: number | null;
    blocked_tags: string[];
  };
  entries: {
    id: string;
    kind: string;
    channel: string | null;
    amount_cents: number;
    note: string;
    created_at: string;
    refunded: boolean;
    lines: { name: string; quantity: number; unit_price_cents: number }[];
    order: { id: string; status: string; version: number } | null;
  }[];
};
const money = (cents: number) =>
  (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const cents = (value: FormDataEntryValue | null) =>
  Math.round(Number(value) * 100);
const tagLabel = (tag: string) =>
  (
    ({
      gluten: "Glúten",
      lactose: "Lactose",
      peanut: "Amendoim",
      sugar: "Açúcar",
      egg: "Ovo",
      soy: "Soja",
    }) as Record<string, string>
  )[tag] || tag.charAt(0).toUpperCase() + tag.slice(1);
const normalizeTags = (value: string) =>
  value
    .split(",")
    .map((t) =>
      t
        .normalize("NFD")
        .replace(/\p{Diacritic}/gu, "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "_"),
    )
    .filter(Boolean);
export function CommerceView({ base, role }: { base: string; role: string }) {
  const selectedStudent = useRef("");
  const requestNumber = useRef(0);
  const staff = ["director", "secretary"].includes(role),
    [products, setProducts] = useState<Product[]>([]),
    [students, setStudents] = useState<Row[]>([]),
    [student, setStudent] = useState(""),
    [statement, setStatement] = useState<Statement | null>(null),
    [channel, setChannel] = useState(staff ? "canteen" : "store"),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [cart, setCart] = useState<Record<string, number>>({}),
    [pending, setPending] = useState<{
      key: string;
      channel: string;
      lines: { product_id: string; quantity: number; version: number }[];
    } | null>(null),
    [edit, setEdit] = useState<Product | null>(null),
    [creditKey, setCreditKey] = useState(""),
    [action, setAction] = useState<{
      id: string;
      kind: "refund" | "delivery";
      version: number;
      key: string;
    } | null>(null),
    [page, setPage] = useState(0);
  async function catalog() {
    setProducts(await allRows<Product>(base + "/inventory"));
  }
  async function load(id = student, offset = page) {
    if (!id) return;
    const number = ++requestNumber.current;
    const data = await api<Statement>(
      base + `/wallets/${id}?limit=30&offset=${offset * 30}`,
    );
    if (id === selectedStudent.current && number === requestNumber.current)
      setStatement(data);
  }
  useEffect(() => {
    setCreditKey(crypto.randomUUID());
    catalog().catch((e) => setError(e.message));
    (staff
      ? allRows(base + "/students")
      : api<{ students: Row[] }>(base + "/portal?limit=100").then(
          (d) => d.students,
        )
    )
      .then(setStudents)
      .catch((e) => setError(e.message));
  }, [base, staff]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [student, page]); // eslint-disable-line react-hooks/exhaustive-deps
  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function product(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      f = new FormData(form);
    await run(async () => {
      const body = {
        channel: f.get("channel"),
        code: f.get("code"),
        name: f.get("name"),
        price_cents: cents(f.get("price")),
        stock: Number(f.get("stock")),
        tags: normalizeTags(String(f.get("tags") || "")),
        active: f.has("active"),
      };
      await api(base + "/inventory" + (edit ? "/" + edit.id : ""), {
        method: edit ? "PUT" : "POST",
        body: JSON.stringify(
          edit ? { ...body, version: edit.version, note: f.get("note") } : body,
        ),
      });
      setEdit(null);
      form.reset();
      await catalog();
      setMessage("Catálogo e estoque atualizados.");
    });
  }
  async function buy() {
    if (!student) return;
    await run(async () => {
      const body = pending || {
        key: crypto.randomUUID(),
        channel,
        lines: Object.entries(cart)
          .filter(([, q]) => q > 0)
          .map(([product_id, quantity]) => ({
            product_id,
            quantity,
            version: products.find((p) => p.id === product_id)!.version,
          })),
      };
      setPending(body);
      try {
        await api(base + `/wallets/${student}/purchase`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        setCart({});
        setPending(null);
        await Promise.all([catalog(), load()]);
        setMessage("Operação registrada na carteira e no estoque.");
      } catch (e) {
        if ((e as ApiError).status >= 400 && (e as ApiError).status < 500) {
          setPending(null);
          await catalog();
        }
        throw e;
      }
    });
  }
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Carteira, cantina e loja</h1>
          <p>
            Saldo interno, catálogo, estoque, limites da cantina e pedidos
            escolares.
          </p>
        </div>
      </div>
      <p>
        Créditos são lançados manualmente pela escola após conferência do
        recebimento. Pix, boleto e cartão dependem da integração de pagamentos.
      </p>
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
            aria-label="Aluno da carteira"
            disabled={busy || !!pending}
            value={student}
            onChange={(e) => {
              selectedStudent.current = e.target.value;
              requestNumber.current++;
              setStudent(e.target.value);
              setStatement(null);
              setCart({});
              setPage(0);
              setAction(null);
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
        {statement && (
          <>
            <h2>
              {statement.student} · Saldo {money(statement.balance_cents)}
            </h2>
            <p>
              Limite diário da cantina:{" "}
              {statement.policy.daily_limit_cents === null
                ? "Sem limite configurado"
                : money(statement.policy.daily_limit_cents)}{" "}
              · Marcadores bloqueados:{" "}
              {statement.policy.blocked_tags.map(tagLabel).join(", ") ||
                "Nenhum"}
            </p>
            {(staff || role === "guardian") && (
              <details>
                <summary>Configurar limites e bloqueios alimentares</summary>
                <p>
                  Os bloqueios comparam os marcadores informados pela escola nos
                  produtos. A família e a equipe devem conferir essas
                  informações.
                </p>
                <form
                  className="record-form"
                  key={student + statement.policy.version}
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    run(async () => {
                      await api(base + `/wallets/${student}/policy`, {
                        method: "PUT",
                        body: JSON.stringify({
                          version: statement.policy.version,
                          daily_limit_cents:
                            f.get("limit") === ""
                              ? null
                              : cents(f.get("limit")),
                          blocked_tags: f.getAll("blocked").map(String),
                        }),
                      });
                      await load();
                      setMessage("Limites atualizados.");
                    });
                  }}
                >
                  <label className="field">
                    Limite diário em R$ (vazio = sem limite; 0 = bloquear
                    consumo)
                    <input
                      type="number"
                      name="limit"
                      step="0.01"
                      min={0}
                      max={100000}
                      defaultValue={
                        statement.policy.daily_limit_cents === null
                          ? ""
                          : statement.policy.daily_limit_cents / 100
                      }
                    />
                  </label>
                  <fieldset>
                    <legend>Bloquear produtos com estes marcadores</legend>
                    {Array.from(
                      new Set([
                        ...products.flatMap((p) => p.tags),
                        ...statement.policy.blocked_tags,
                      ]),
                    )
                      .sort()
                      .map((tag) => (
                        <label className="checkbox-field" key={tag}>
                          <input
                            name="blocked"
                            type="checkbox"
                            value={tag}
                            defaultChecked={statement.policy.blocked_tags.includes(
                              tag,
                            )}
                          />
                          {tagLabel(tag)}
                        </label>
                      ))}
                  </fieldset>
                  <Button disabled={busy}>Salvar limites</Button>
                </form>
              </details>
            )}
            {staff && (
              <form
                className="record-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget,
                    f = new FormData(form);
                  run(async () => {
                    await api(base + `/wallets/${student}/credit`, {
                      method: "POST",
                      body: JSON.stringify({
                        key: creditKey,
                        amount_cents: cents(f.get("amount")),
                        note: f.get("note"),
                      }),
                    });
                    setCreditKey(crypto.randomUUID());
                    form.reset();
                    await load();
                    setMessage("Crédito manual registrado.");
                  });
                }}
              >
                <h3>Registrar crédito conferido pela escola</h3>
                <label className="field">
                  Valor recebido (R$)
                  <input
                    name="amount"
                    type="number"
                    step="0.01"
                    min={0.01}
                    max={100000}
                    required
                  />
                </label>
                <label className="field">
                  Referência / observação visível à família
                  <input name="note" minLength={3} maxLength={1000} required />
                </label>
                <Button disabled={busy}>Registrar crédito manual</Button>
              </form>
            )}
          </>
        )}
      </section>
      <section className="panel record-form">
        <h2>Catálogo</h2>
        <label className="field">
          Canal
          <select
            aria-label="Canal de compra"
            disabled={!!pending || busy}
            value={channel}
            onChange={(e) => {
              setChannel(e.target.value);
              setCart({});
            }}
          >
            <option value="canteen">Cantina</option>
            <option value="store">Loja e eventos</option>
          </select>
        </label>
        {products
          .filter((p) => p.channel === channel)
          .map((p) => (
            <article className="learning-record" key={p.id}>
              <div>
                <h3>{p.name}</h3>
                <p>
                  {money(p.price_cents)} · {p.stock} em estoque{" "}
                  {p.active ? "" : "· Inativo"}
                </p>
                <p>Marcadores: {p.tags.map(tagLabel).join(", ") || "Nenhum"}</p>
                {staff && (
                  <Button variant="outline" onClick={() => setEdit(p)}>
                    Editar produto / estoque
                  </Button>
                )}
              </div>
              {p.active &&
                (staff || (role === "guardian" && channel === "store")) && (
                  <label className="field">
                    Quantidade de {p.name}
                    <input
                      aria-label={"Quantidade de " + p.name}
                      type="number"
                      min={0}
                      max={Math.min(p.stock, 100)}
                      disabled={!!pending || busy}
                      value={cart[p.id] || 0}
                      onChange={(e) =>
                        setCart((old) => ({
                          ...old,
                          [p.id]: Math.max(0, Number(e.target.value)),
                        }))
                      }
                    />
                  </label>
                )}
            </article>
          ))}
        {(staff || (role === "guardian" && channel === "store")) && (
          <>
            <p>
              Total:{" "}
              {money(
                Object.entries(cart).reduce(
                  (sum, [id, q]) =>
                    sum +
                    (products.find((p) => p.id === id)?.price_cents || 0) * q,
                  0,
                ),
              )}
            </p>
            <Button
              disabled={
                busy ||
                !student ||
                (!pending && !Object.values(cart).some((q) => q > 0))
              }
              onClick={buy}
            >
              {pending
                ? "Confirmar resultado da operação"
                : "Confirmar compra com saldo da carteira"}
            </Button>
          </>
        )}
      </section>
      {staff && (
        <details className="panel" open={!!edit}>
          <summary>
            {edit ? "Editar produto" : "Cadastrar produto / evento"}
          </summary>
          <form
            className="record-form"
            key={edit?.id || "new"}
            onSubmit={product}
          >
            <label className="field">
              Canal
              <select name="channel" defaultValue={edit?.channel || channel}>
                <option value="canteen">Cantina</option>
                <option value="store">Loja e eventos</option>
              </select>
            </label>
            <label className="field">
              Código do produto
              <input
                name="code"
                minLength={1}
                maxLength={60}
                defaultValue={edit?.code || ""}
                required
              />
            </label>
            <label className="field">
              Nome
              <input
                name="name"
                minLength={2}
                maxLength={160}
                defaultValue={edit?.name || ""}
                required
              />
            </label>
            <label className="field">
              Preço (R$)
              <input
                name="price"
                type="number"
                step="0.01"
                min={0.01}
                max={100000}
                defaultValue={edit ? edit.price_cents / 100 : undefined}
                required
              />
            </label>
            <label className="field">
              Estoque disponível
              <input
                name="stock"
                type="number"
                min={0}
                max={1000000}
                defaultValue={edit?.stock ?? 0}
                required
              />
            </label>
            <label className="field">
              Marcadores alimentares, separados por vírgula
              <input name="tags" defaultValue={edit?.tags.join(", ") || ""} />
            </label>
            <label>
              <input
                name="active"
                type="checkbox"
                defaultChecked={edit?.active ?? true}
              />{" "}
              Produto ativo
            </label>
            {edit && (
              <label className="field">
                Motivo da alteração
                <input name="note" minLength={3} maxLength={1000} required />
              </label>
            )}
            <Button disabled={busy}>Salvar produto</Button>
            {edit && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setEdit(null)}
              >
                Cancelar edição
              </Button>
            )}
          </form>
        </details>
      )}
      {statement && (
        <section className="panel">
          <h2>Extrato e pedidos</h2>
          {statement.entries.map((e) => (
            <article className="learning-record" key={e.id}>
              <div>
                <h3>
                  {e.kind === "credit"
                    ? "Crédito manual"
                    : e.kind === "refund"
                      ? "Estorno na carteira"
                      : e.channel === "canteen"
                        ? "Consumo da cantina"
                        : "Pedido na loja"}{" "}
                  · {money(e.amount_cents)}
                </h3>
                <p>
                  {new Date(e.created_at).toLocaleString("pt-BR")} · {e.note}
                </p>
                {e.lines.map((l, i) => (
                  <p key={i}>
                    {l.quantity} × {l.name} · {money(l.unit_price_cents)}
                  </p>
                ))}
                {e.order && (
                  <p>
                    Pedido:{" "}
                    {e.order.status === "placed"
                      ? "Aguardando entrega"
                      : e.order.status === "delivered"
                        ? "Entregue"
                        : "Cancelado"}
                  </p>
                )}
                {e.refunded && <p>Estornado na carteira.</p>}
              </div>
              {staff && (
                <div>
                  {e.kind === "debit" && !e.refunded && (
                    <Button
                      variant="outline"
                      onClick={() =>
                        setAction({
                          id: e.id,
                          kind: "refund",
                          version: 0,
                          key: crypto.randomUUID(),
                        })
                      }
                    >
                      Estornar na carteira
                    </Button>
                  )}
                  {e.order?.status === "placed" && (
                    <Button
                      variant="outline"
                      onClick={() =>
                        setAction({
                          id: e.order!.id,
                          kind: "delivery",
                          version: e.order!.version,
                          key: crypto.randomUUID(),
                        })
                      }
                    >
                      Registrar entrega
                    </Button>
                  )}
                </div>
              )}
            </article>
          ))}
          <div className="learning-toolbar">
            <Button
              variant="outline"
              disabled={page === 0 || busy}
              onClick={() => setPage((p) => p - 1)}
            >
              Anterior
            </Button>
            <span>Página {page + 1}</span>
            <Button
              variant="outline"
              disabled={statement.entries.length < 30 || busy}
              onClick={() => setPage((p) => p + 1)}
            >
              Próxima
            </Button>
          </div>
          {action && (
            <form
              className="record-form"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                run(async () => {
                  await api(
                    base +
                      (action.kind === "refund"
                        ? `/wallet-entries/${action.id}/refund`
                        : `/store-orders/${action.id}/deliver`),
                    {
                      method: "POST",
                      body: JSON.stringify(
                        action.kind === "refund"
                          ? {
                              key: action.key,
                              note: f.get("note"),
                              restock: f.has("restock"),
                            }
                          : { version: action.version, note: f.get("note") },
                      ),
                    },
                  );
                  setAction(null);
                  await Promise.all([catalog(), load()]);
                  setMessage("Operação registrada.");
                });
              }}
            >
              <h3>
                {action.kind === "refund"
                  ? "Estorno interno"
                  : "Entrega do pedido"}
              </h3>
              <label className="field">
                Motivo / confirmação
                <input name="note" minLength={10} maxLength={1000} required />
              </label>
              {action.kind === "refund" && (
                <label>
                  <input type="checkbox" name="restock" /> Repor itens no
                  estoque (houve devolução)
                </label>
              )}
              <Button disabled={busy}>Confirmar registro</Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAction(null)}
              >
                Cancelar
              </Button>
            </form>
          )}
        </section>
      )}
    </div>
  );
}
