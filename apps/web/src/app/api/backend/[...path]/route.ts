import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";
const API_URL = process.env.API_URL || "http://127.0.0.1:8100";
const APP_ORIGIN = process.env.APP_ORIGIN || "http://localhost:3100";
const COOKIE = "siesco_session";
type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: Context) {
  const { path } = await context.params;
  if (path.some(p => !/^[a-zA-Z0-9_-]+$/.test(p)) || !["auth", "me", "platform", "institutions"].includes(path[0])) {
    return NextResponse.json({ error: { message: "Rota inválida." } }, { status: 404 });
  }
  if (!["GET", "HEAD"].includes(request.method) && request.headers.get("origin") !== APP_ORIGIN) {
    return NextResponse.json({ error: { message: "Origem da requisição inválida." } }, { status: 403 });
  }
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  const endpoint = path.join("/");
  const isLogin = endpoint === "auth/login";
  if (!isLogin && !token) return NextResponse.json({ error: { message: "Entre para continuar." } }, { status: 401 });
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();
  if (body && new TextEncoder().encode(body).length > 65536) return NextResponse.json({ error: { message: "Requisição muito grande." } }, { status: 413 });
  try {
    const upstream = await fetch(`${API_URL}/api/v1/${endpoint}${request.nextUrl.search}`, {
      method: request.method, headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body, cache: "no-store", signal: AbortSignal.timeout(15000), redirect: "error",
    });
    const data = upstream.status === 204 ? null : await upstream.json();
    const response = new NextResponse(upstream.status === 204 ? null : JSON.stringify(isLogin && upstream.ok ? { ok: true } : data), {
      status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
    if (isLogin && upstream.ok) response.cookies.set(COOKIE, data.access_token, { httpOnly: true, secure: true, sameSite: "strict", path: "/", maxAge: data.expires_in });
    if (upstream.status === 401 || (endpoint === "auth/logout" && upstream.ok)) response.cookies.set(COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
    return response;
  } catch {
    return NextResponse.json({ error: { message: "O serviço está indisponível. Tente novamente em instantes." } }, { status: 503 });
  }
}
export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE };
