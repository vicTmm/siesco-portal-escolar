// @vitest-environment node
import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
const session = vi.hoisted(() => ({ token: "opaque-token" as string | undefined }));
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => session.token ? { value: session.token } : undefined }) }));
import { GET, POST } from "@/app/api/backend/[...path]/route";

const context = (path: string) => ({ params: Promise.resolve({ path: path.split("/") }) });
beforeEach(() => { vi.restoreAllMocks(); session.token = "opaque-token"; });

it("bloqueia mutação de origem diferente antes de acessar API", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch");
  const response = await POST(new NextRequest("http://localhost:3100/api/backend/auth/logout", { method: "POST", headers: { origin: "https://outside.example.com" } }), context("auth/logout"));
  expect(response.status).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});

it("nega consulta sem sessão", async () => {
  session.token = undefined;
  expect((await GET(new NextRequest("http://localhost:3100/api/backend/me"), context("me"))).status).toBe(401);
});

it("mantém token de login fora do JSON e protege cookie", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ access_token: "secret-session", expires_in: 28800 }), { status: 200 }));
  const response = await POST(new NextRequest("http://localhost:3100/api/backend/auth/login", { method: "POST", headers: { origin: "http://localhost:3100" }, body: JSON.stringify({ email: "demo@example.com", password: "not-real" }) }), context("auth/login"));
  expect(await response.json()).toEqual({ ok: true });
  expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  expect(response.headers.get("set-cookie")).toContain("SameSite=strict");
  expect(response.headers.get("set-cookie")).toContain("Secure");
});

it("preserva erro de permissão da API e injeta sessão do servidor", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { message: "Sem permissão" } }), { status: 403 }));
  const response = await GET(new NextRequest("http://localhost:3100/api/backend/me"), context("me"));
  expect(response.status).toBe(403);
  expect((await response.json()).error.message).toBe("Sem permissão");
  expect(fetcher.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer opaque-token" });
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("limpa cookie de sessão expirada", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { message: "Expirou" } }), { status: 401 }));
  const response = await GET(new NextRequest("http://localhost:3100/api/backend/me"), context("me"));
  expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
});

it("falha de rede produz erro recuperável sem detalhes internos", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("internal-network-secret"));
  const response = await GET(new NextRequest("http://localhost:3100/api/backend/me"), context("me"));
  expect(response.status).toBe(503);
  expect(await response.text()).not.toContain("internal-network-secret");
});

it("rejeita segmento de caminho não permitido", async () => {
  expect((await GET(new NextRequest("http://localhost:3100/api/backend/me"), context("institutions/../auth"))).status).toBe(404);
});
