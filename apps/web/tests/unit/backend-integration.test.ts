// @vitest-environment node
import { expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
const session = vi.hoisted(() => ({ token: undefined as string | undefined }));
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => session.token ? { value: session.token } : undefined }) }));
import { GET, POST } from "@/app/api/backend/[...path]/route";

it.skipIf(process.env.INTEGRATION_API !== "true")("integra o BFF com a API real: login, consulta e revogação", async () => {
  const context = (path: string) => ({ params: Promise.resolve({ path: path.split("/") }) });
  const request = (path: string, body?: unknown) => new NextRequest(`http://localhost:3100/api/backend/${path}`, body ? { method: "POST", headers: { origin: "http://localhost:3100" }, body: JSON.stringify(body) } : undefined);
  const login = await POST(request("auth/login", { email: "director@aurora.example.com", password: process.env.DEMO_PASSWORD }), context("auth/login"));
  expect(login.status).toBe(200);
  session.token = login.cookies.get("siesco_session")?.value;
  expect(session.token).toBeTruthy();
  const me = await GET(request("me"), context("me"));
  expect(me.status).toBe(200);
  const tenant = (await me.json()).memberships[0].institution_id;
  const path = `institutions/${tenant}/dashboard`;
  const dashboard = await GET(request(path), context(path));
  expect(dashboard.status).toBe(200);
  expect((await dashboard.json()).counts.students).toBeGreaterThanOrEqual(4);
  const logout = await POST(request("auth/logout", {}), context("auth/logout"));
  expect(logout.status).toBe(204);
  expect((await GET(request("me"), context("me"))).status).toBe(401);
});
