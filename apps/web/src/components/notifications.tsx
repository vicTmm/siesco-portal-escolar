"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
type Item = {
  key: string;
  title: string;
  message: string;
  destination: string;
};
export function NotificationsView({
  base,
  navigate,
}: {
  base: string;
  navigate: (destination: string) => void;
}) {
  const [items, setItems] = useState<Item[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(0),
    [error, setError] = useState("");
  async function load() {
    const result = await api<{ count: number; items: Item[] }>(
      base + `/notifications?limit=30&offset=${page * 30}`,
    );
    setItems(result.items);
    setTotal(result.count);
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
    const timer = setInterval(() => {
      if (!document.hidden) load().catch((e) => setError(e.message));
    }, 30000);
    return () => clearInterval(timer);
  }, [base, page]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="school-workflow">
      <div className="page-heading">
        <div>
          <h1>Notificações</h1>
          <p>
            {total} lembretes internos de comunicados, atendimentos e rotina
            escolar.
          </p>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!items.length && <p className="panel">Nenhum lembrete pendente.</p>}
      {items.map((n) => (
        <article key={n.key} className="panel">
          <h2>{n.title}</h2>
          <p>{n.message}</p>
          <div className="learning-toolbar">
            <Button onClick={() => navigate(n.destination)}>Abrir</Button>
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  await api(base + "/notifications/dismiss", {
                    method: "POST",
                    body: JSON.stringify({ key: n.key }),
                  });
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              Dispensar lembrete
            </Button>
          </div>
        </article>
      ))}
      <div className="learning-toolbar">
        <Button
          variant="outline"
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
        >
          Anterior
        </Button>
        <span>Página {page + 1}</span>
        <Button
          variant="outline"
          disabled={items.length < 30}
          onClick={() => setPage((p) => p + 1)}
        >
          Próxima
        </Button>
      </div>
    </div>
  );
}
