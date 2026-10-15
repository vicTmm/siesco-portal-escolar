import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";
const API_URL = process.env.API_URL || "http://127.0.0.1:8100";
const APP_ORIGIN = process.env.APP_ORIGIN || "http://localhost:3100";
const COOKIE = "siesco_session";
type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: Context) {
  const { path } = await context.params;
  if (path.some(p => !/^[a-zA-Z0-9_-]+$/.test(p)) || !["auth", "me", "platform", "institutions", "verify-document"].includes(path[0])) {
    return NextResponse.json({ error: { message: "Rota inválida." } }, { status: 404 });
  }
  if (!["GET", "HEAD"].includes(request.method) && request.headers.get("origin") !== APP_ORIGIN) {
    return NextResponse.json({ error: { message: "Origem da requisição inválida." } }, { status: 403 });
  }
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  const endpoint = path.join("/");
  const isLogin = endpoint === "auth/login";
  const publicAuth = (path[0] === "verify-document" && path.length === 2 && request.method === "GET") || ["auth/login", "auth/forgot-password", "auth/reset-password"].includes(endpoint);
  if (!publicAuth && !token) return NextResponse.json({ error: { message: "Entre para continuar." } }, { status: 401 });
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();
  const bodyLimit = /^institutions\/[a-zA-Z0-9_-]+\/service-records\/[a-zA-Z0-9_-]+\/attachments$/.test(endpoint) ? 2900000 : endpoint.endsWith("/offline-sync") ? 300000 : 65536;
  if (body && new TextEncoder().encode(body).length > bodyLimit) return NextResponse.json({ error: { message: "Requisição muito grande." } }, { status: 413 });
  try {
    const upstream = await fetch(`${API_URL}/api/v1/${endpoint}${request.nextUrl.search}`, {
      method: request.method, headers: { "Content-Type": "application/json", ...(request.headers.get("x-membership-id") ? {"X-Membership-Id":request.headers.get("x-membership-id")!}:{}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body, cache: "no-store", signal: AbortSignal.timeout(/^institutions\/[a-zA-Z0-9_-]+\/fiscal\/invoices\/[a-zA-Z0-9_-]+\/(emit|reconcile)$/.test(endpoint) ? 70000 : 15000), redirect: "error",
    });
    const data = upstream.status === 204 ? null : await upstream.json();
    const response = new NextResponse(upstream.status === 204 ? null : JSON.stringify(isLogin && upstream.ok ? { ok: true } : data), {
      status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
    if (isLogin && upstream.ok) response.cookies.set(COOKIE, data.access_token, { httpOnly: true, secure: true, sameSite: "strict", path: "/", maxAge: data.expires_in });
    if (upstream.status === 401 || (["auth/logout", "auth/change-password", "auth/reset-password"].includes(endpoint) && upstream.ok)) response.cookies.set(COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
    return response;
  } catch {
    return NextResponse.json({ error: { message: "O serviço está indisponível. Tente novamente em instantes." } }, { status: 503 });
  }
}
export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE };
