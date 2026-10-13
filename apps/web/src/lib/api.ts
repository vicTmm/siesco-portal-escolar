export type Row = { id: string; [key: string]: string | number | boolean | null };
export type Membership = { institution_id: string; institution_name: string; school_id: string; role: string };
export type User = { id: string; name: string; email: string; platform_admin: boolean; memberships: Membership[] };
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers }, cache: "no-store" });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const fields = data?.error?.fields?.map((f: { field: string; message: string }) => `${f.field}: ${f.message}`).join(" · ");
    throw new ApiError(response.status, fields || data?.error?.message || "Não foi possível concluir a operação.");
  }
  return data;
}
export async function allRows(path: string): Promise<Row[]> {
  const result: Row[] = [];
  for (let offset = 0; ; offset += 100) {
    const rows = await api<Row[]>(`${path}?limit=100&offset=${offset}`);
    result.push(...rows);
    if (rows.length < 100) return result;
  }
}
