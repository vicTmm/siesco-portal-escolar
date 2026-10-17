import { afterEach, expect, it, vi } from "vitest";
import { allRows } from "@/lib/api";
afterEach(() => vi.unstubAllGlobals());
it("preserva o filtro de aluno ao buscar páginas seguintes", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () =>
        Array.from({ length: 100 }, (_, n) => ({ id: String(n) })),
    })
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [{ id: "100" }],
    });
  vi.stubGlobal("fetch", fetcher);
  const rows = await allRows(
    "institutions/demo/psychology?student_id=student-a",
  );
  expect(rows).toHaveLength(101);
  expect(fetcher.mock.calls.map((c) => c[0])).toEqual([
    "/api/backend/institutions/demo/psychology?student_id=student-a&limit=100&offset=0",
    "/api/backend/institutions/demo/psychology?student_id=student-a&limit=100&offset=100",
  ]);
});
