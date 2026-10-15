"use client";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Pencil, Plus, Search, XCircle } from "lucide-react";
import { EnrollmentActions } from "./enrollment-actions";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { allRows, api, ApiError, type Row } from "@/lib/api";
import { moduleIcons } from "@/lib/icons";
import { catalogs, labels, referenceSources, roles, shifts } from "@/lib/catalogs";

export function CatalogView({ resource, base, role, expired }: { resource: string; base: string; role: string; expired: () => void }) {
  const config = catalogs[resource];
  const ResourceIcon = moduleIcons[resource as keyof typeof moduleIcons];
  const path = resource === "institutions" ? "platform/institutions" : `${base}/${resource}`;
  const [rows, setRows] = useState<Row[]>([]);
  const [references, setReferences] = useState<Record<string, Row[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const serverSearch = ["students", "guardians", "teachers", "subjects", "classes", "academic-years", "academic-terms", "curricula", "institutions"].includes(resource);
  useEffect(() => { const timer = setTimeout(() => { setQuery(search); setPage(0); }, 250); return () => clearTimeout(timer); }, [search]);
  const [revision, setRevision] = useState(0);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const canWrite = config.writers.includes(role);

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const sources = new Set(config.fields.filter(f => f.source && f.source !== "dynamic").map(f => f.source!));
    if (resource === "accounts") ["students", "teachers", "guardians"].forEach(s => sources.add(s));
    Promise.all([api<Row[]>(`${path}?limit=50&offset=${page * 50}${serverSearch ? `&q=${encodeURIComponent(query)}` : ""}`), Promise.all([...sources].map(async s => [s, await allRows(`${base}/${s}`)] as const))])
      .then(([data, refs]) => { if (active) { setRows(data); setReferences(Object.fromEntries(refs)); } })
      .catch(e => { if (active) { setError(e.message); if (e instanceof ApiError && e.status === 401) expired(); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, page, revision, base, config, resource, expired, query, serverSearch]);

  function start(row: Row | null = null) {
    setEditing(row); setFormError("");
    setValues(Object.fromEntries(config.fields.map(f => [f.key, row ? (typeof row[f.key] === "boolean" ? row[f.key] as boolean : String(row[f.key] ?? "")) : f.type === "checkbox" ? false : ["academic_year", "year"].includes(f.key) ? String(new Date().getFullYear()) : ["version", "sequence"].includes(f.key) ? "1" : f.key === "capacity" ? "30" : ""])));
    setOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setFormError("");
    const payload: Record<string, unknown> = {};
    for (const field of config.fields) {
      if (field.key === "person_id" && !["teacher", "student", "guardian"].includes(String(values.role))) continue;
      if (field.key === "curriculum_id" && !field.required && !values[field.key]) { payload[field.key] = null; continue; }
      payload[field.key] = field.type === "number" ? Number(values[field.key]) : values[field.key];
    }
    try {
      await api(`${path}${editing ? "/" + editing.id : ""}`, { method: editing ? "PUT" : "POST", body: JSON.stringify(payload) });
      setOpen(false); setNotice(editing ? "Alterações salvas." : "Cadastro realizado com sucesso."); setRevision(n => n + 1);
    } catch (e) { setFormError(e instanceof Error ? e.message : "Erro ao salvar."); }
    finally { setSaving(false); }
  }

  async function revoke(row: Row) {
    const action = resource === "enrollments" ? "Cancelar esta matrícula? O histórico será preservado." : resource === "curriculum-subjects" ? "Remover esta disciplina do currículo em rascunho?" : "Revogar este acesso? A alteração será aplicada imediatamente.";
    if (!window.confirm(action)) return;
    setSaving(true); setError("");
    try {
      await api(`${path}/${row.id}${resource === "enrollments" ? "/cancel" : ""}`, { method: resource === "enrollments" ? "POST" : "DELETE" });
      setNotice("Alteração registrada."); setRevision(n => n + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "Erro ao atualizar."); }
    finally { setSaving(false); }
  }

  function locked(row: Row) {
    return row.status === "published" || (resource === "curriculum-subjects" && references.curricula?.find(c => c.id === row.curriculum_id)?.status === "published");
  }

  async function publish(row: Row) {
    if (!window.confirm("Publicar este currículo? A versão e suas disciplinas ficarão protegidas contra alterações.")) return;
    setSaving(true); setError("");
    try { await api(`${path}/${row.id}/publish`, { method: "POST" }); setNotice("Currículo publicado. Para mudanças, cadastre uma nova versão."); setRevision(n => n + 1); }
    catch (e) { setError(e instanceof Error ? e.message : "Erro ao publicar."); }
    finally { setSaving(false); }
  }

  function display(row: Row, key: string) {
    const value = row[key];
    if (referenceSources[key]) { const ref = references[referenceSources[key]]?.find(r => r.id === value); return !value ? "Não vinculado" : ref ? String(ref.name) + (referenceSources[key] === "curricula" ? ` · v${ref.version}` : "") : "Registro indisponível"; }
    if (["birth_date", "start_date", "end_date"].includes(key)) return String(value).split("-").reverse().join("/");
    if (key === "role") return roles.find(r => r[0] === value)?.[1] || value;
    if (key === "shift") return shifts.find(r => r[0] === value)?.[1] || value;
    if (key === "status") return ({ active: "Ativa", cancelled: "Cancelada", draft: "Rascunho", published: "Publicado" } as Record<string, string>)[String(value)] || value;
    if (key === "needs_review") return value ? "Revisar datas importadas" : "Datas definidas";
    if (key === "verified") return value ? "Verificado" : "Sem acesso";
    return value || "—";
  }
  const filtered = serverSearch ? rows : rows.filter(row => config.columns.some(key => String(display(row, key)).toLowerCase().includes(search.toLowerCase())));

  return <>
    <div className="page-heading"><div><div className="eyebrow">GESTÃO ESCOLAR</div><h1>{config.title}</h1><p>{config.description}</p></div>{canWrite && <Button onClick={() => start()}><Plus size={17} /> Cadastrar {config.singular}</Button>}</div>
    {notice && <div className="success" role="status"><CheckCircle2 size={18} />{notice}</div>}
    {error && <div className="error" role="alert">{error} <Button variant="outline" size="sm" onClick={() => setRevision(n => n + 1)}>Tentar novamente</Button></div>}
    <section className="panel catalog-panel">
      <div className="table-toolbar"><div><h2>Todos os registros</h2><p>{canWrite ? "Consulte e organize os cadastros da instituição." : "Consulta disponível para seu perfil."}</p></div><label className="search"><Search size={17} /><input aria-label={serverSearch ? "Buscar em todos os registros" : "Buscar nesta página"} placeholder={serverSearch ? "Buscar em todos os registros…" : "Buscar nesta página…"} value={search} onChange={e => setSearch(e.target.value)} /></label></div>
      {loading ? <div className="skeleton-stack" role="status" aria-label="Carregando registros">{[1, 2, 3, 4].map(i => <div key={i} className="skeleton" />)}</div> : filtered.length ? <div className="table-scroll"><table><thead><tr>{config.columns.map(key => <th key={key}>{labels[key]}</th>)}{canWrite && <th>Ações</th>}</tr></thead><tbody>{filtered.map(row => <tr key={row.id}>{config.columns.map((key, index) => <td key={key}>{index === 0 && key === "name" ? <span className="table-person"><span className="mini-avatar">{String(row.name).slice(0, 1)}</span><strong>{display(row, key)}</strong></span> : ["status", "verified"].includes(key) ? <span className={`badge ${["active", "published"].includes(String(row[key])) || row[key] === true ? "green" : "neutral"}`}>{display(row, key)}</span> : display(row, key)}</td>)}{canWrite && <td className="row-actions">{resource === "enrollments" && <EnrollmentActions row={row} base={base} classes={references.classes || []} onDone={() => { setNotice("Movimentação registrada."); setRevision(n => n + 1); }} />}{resource === "accounts" && <Button disabled={saving} variant="ghost" size="sm" onClick={async () => { setSaving(true); setError(""); try { await api(`${path}/${row.id}/invite`, { method: "POST" }); setNotice("Convite enviado para o e-mail da conta."); } catch (e) { setError(e instanceof Error ? e.message : "Falha ao enviar convite."); } finally { setSaving(false); } }}>Enviar convite</Button>}{resource === "curricula" && row.status === "draft" && <Button disabled={saving} variant="ghost" size="sm" onClick={() => publish(row)}><CheckCircle2 size={15} />Publicar</Button>}{config.editable && !locked(row) && <Button variant="ghost" size="sm" aria-label={`Editar ${row.name || display(row, "subject_id")}`} onClick={() => start(row)}><Pencil size={15} />Editar</Button>}{["accounts", "guardian-links", "curriculum-subjects"].includes(resource) && <Button disabled={saving || locked(row) || row.status === "cancelled" || row.verified === false} variant="ghost" size="sm" onClick={() => revoke(row)}><XCircle size={15} />{resource === "enrollments" ? "Cancelar" : resource === "curriculum-subjects" ? "Remover" : "Revogar"}</Button>}</td>}</tr>)}</tbody></table></div> : <div className="empty"><ResourceIcon size={30} /><h3>{search ? "Nenhum resultado nesta página" : "Tudo pronto para começar"}</h3><p>{search ? "Experimente buscar por outro termo." : `Os cadastros de ${config.title.toLowerCase()} aparecerão aqui.`}</p>{canWrite && !search && <Button variant="outline" onClick={() => start()}>Criar primeiro cadastro</Button>}</div>}
      <div className="table-footer"><span>Página {page + 1} · {filtered.length} registros exibidos</span><div><Button variant="ghost" size="sm" disabled={page === 0 || loading} onClick={() => { setPage(n => n - 1); }}><ArrowLeft size={15} />Anterior</Button><Button variant="ghost" size="sm" disabled={rows.length < 50 || loading} onClick={() => { setPage(n => n + 1); }}>Próxima<ArrowRight size={15} /></Button></div></div>
    </section>
    <Dialog open={open} onOpenChange={v => { if (!saving) setOpen(v); }}><DialogContent><DialogTitle className="dialog-title">{editing ? "Editar" : "Cadastrar"} {config.singular}</DialogTitle><DialogDescription className="dialog-description">Preencha os dados abaixo. Campos com * são obrigatórios.</DialogDescription>
      <form onSubmit={submit} className="record-form">{config.fields.map(field => {
        let source = field.source;
        if (source === "dynamic") { source = ({ teacher: "teachers", student: "students", guardian: "guardians" } as Record<string, string>)[String(values.role)]; if (!source) return null; }
        const required = field.required || field.key === "person_id";
        const available = source ? (references[source] || []).filter(row => source !== "curricula" || (resource === "classes" ? row.status === "published" : row.status === "draft")) : [];
        const options = source ? available.map(row => [row.id, String(row.name) + (source === "classes" ? ` · ${row.academic_year}` : source === "curricula" ? ` · v${row.version}` : "")]) : field.options;
        return <label key={field.key} className={field.type === "checkbox" ? "checkbox-field" : "field"}>{field.type === "checkbox" ? <><input type="checkbox" checked={Boolean(values[field.key])} onChange={e => setValues(v => ({ ...v, [field.key]: e.target.checked }))} />{field.label}</> : <><span>{field.label}{required ? " *" : ""}</span>{options ? <select required={required} value={String(values[field.key] || "")} onChange={e => setValues(v => ({ ...v, [field.key]: e.target.value, ...(field.key === "role" ? { person_id: "" } : {}) }))}><option value="">Selecione…</option>{options.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select> : <input type={field.type || "text"} disabled={Boolean(editing) && ((resource === "academic-years" && field.key === "year") || (resource === "curricula" && ["code", "version"].includes(field.key)))} required={required} value={String(values[field.key] || "")} min={field.type === "number" ? field.min : undefined} max={field.type === "number" ? field.max : field.key === "birth_date" ? new Date().toISOString().slice(0, 10) : undefined} minLength={field.type !== "number" ? field.min : undefined} maxLength={field.type !== "number" ? field.max : undefined} autoComplete={field.type === "password" ? "new-password" : "off"} onChange={e => setValues(v => ({ ...v, [field.key]: e.target.value }))} />}</>}</label>;
      })}{formError && <div className="error" role="alert">{formError}</div>}<div className="form-actions"><Button type="button" variant="outline" disabled={saving} onClick={() => setOpen(false)}>Cancelar</Button><Button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar cadastro"}</Button></div></form>
    </DialogContent></Dialog>
  </>;
}
