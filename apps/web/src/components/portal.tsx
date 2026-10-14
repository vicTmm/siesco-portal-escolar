"use client";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ArrowRight, BookOpen, Building2, ClipboardList, GraduationCap, LayoutDashboard, Link2, MessageCircle, LogOut, Menu, School, ShieldCheck, Users, X } from "lucide-react";
import { api, type User } from "@/lib/api";
import { roles } from "@/lib/catalogs";
import { Button } from "./ui/button";
import { CatalogView } from "./catalog";
import { Dashboard } from "./dashboard";
import { WhatsAppDemo } from "./whatsapp";

const navigation = [
  { key: "dashboard", title: "Visão geral", icon: LayoutDashboard, group: "PRINCIPAL" },
  { key: "students", title: "Alunos", icon: GraduationCap, group: "PESSOAS" },
  { key: "guardians", title: "Responsáveis", icon: Users },
  { key: "guardian-links", title: "Vínculos familiares", icon: Link2 },
  { key: "teachers", title: "Professores", icon: Users },
  { key: "academic-years", title: "Anos letivos", icon: BookOpen, group: "ACADÊMICO" },
  { key: "academic-terms", title: "Períodos letivos", icon: ClipboardList },
  { key: "subjects", title: "Disciplinas", icon: BookOpen },
  { key: "curricula", title: "Currículos", icon: BookOpen },
  { key: "curriculum-subjects", title: "Matriz curricular", icon: ClipboardList },
  { key: "classes", title: "Turmas", icon: School },
  { key: "assignments", title: "Atribuições docentes", icon: ClipboardList },
  { key: "enrollments", title: "Matrículas", icon: ClipboardList },
  { key: "whatsapp", title: "Avisos por WhatsApp", icon: MessageCircle, group: "COMUNICAÇÃO" },
  { key: "accounts", title: "Contas e permissões", icon: ShieldCheck, group: "ADMINISTRAÇÃO" },
];

export function Portal() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [tenant, setTenant] = useState("");
  const [view, setView] = useState("dashboard");
  const [mobile, setMobile] = useState(false);
  const [error, setError] = useState("");
  const expired = useCallback(() => { setUser(null); setTenant(""); }, []);
  const loadUser = useCallback(async () => {
    const next = await api<User>("me"); setUser(next); setError("");
    const first = next.memberships[0]; setTenant(first?.institution_id || "");
    setView(next.platform_admin ? "institutions" : ["director", "secretary", "coordinator"].includes(first?.role) ? "dashboard" : "portal");
  }, []);
  useEffect(() => { loadUser().catch(e => { if (e.status !== 401) setError(e.message); }).finally(() => setReady(true)); }, [loadUser]);
  function navigate(next: string) { setView(next); setMobile(false); }
  async function logout() { try { await api("auth/logout", { method: "POST" }); expired(); } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível sair."); } }
  if (!ready) return <main className="fatal" role="status">Abrindo seu espaço escolar…</main>;
  if (!user) return <Login onLogin={loadUser} initialError={error} />;
  const member = user.memberships.find(m => m.institution_id === tenant);
  const role = user.platform_admin && view === "institutions" ? "platform" : member?.role || "";
  const manager = ["director", "secretary", "coordinator"].includes(role);
  const base = `institutions/${tenant}`;
  const roleName = role === "platform" ? "Administração da plataforma" : roles.find(r => r[0] === role)?.[1] || "Sem vínculo ativo";
  const activeTitle = view === "institutions" ? "Instituições" : view === "portal" ? "Meu portal" : navigation.find(n => n.key === view)?.title;
  return <div className="app-shell"><a href="#main" className="skip-link">Pular para conteúdo</a>{mobile && <button className="mobile-scrim" aria-label="Fechar menu" onClick={() => setMobile(false)} />}
    <aside className={`sidebar ${mobile ? "is-open" : ""}`}><div className="brand"><span className="brand-symbol"><GraduationCap size={24} /></span><div>siesco<span>PORTAL ESCOLAR</span></div><button className="mobile-close" aria-label="Fechar menu" onClick={() => setMobile(false)}><X size={20} /></button></div><div className="institution-label"><span className="school-symbol"><Building2 size={19} /></span><div><strong>{member?.institution_name || "Plataforma Siesco"}</strong><span>{member ? "Unidade principal" : "Gestão de instituições"}</span></div></div>
      <nav aria-label="Menu principal">{user.platform_admin ? <button onClick={() => navigate("institutions")} className="nav-link active"><Building2 size={18} />Instituições</button> : manager ? navigation.filter(n => n.key !== "accounts" || role === "director").map(item => <div key={item.key}>{item.group && <div className="nav-group">{item.group}</div>}<button aria-current={view === item.key ? "page" : undefined} className={`nav-link ${view === item.key ? "active" : ""}`} onClick={() => navigate(item.key)}><item.icon size={18} />{item.title}{view === item.key && <span className="active-dot" />}</button></div>) : <button className="nav-link active" onClick={() => navigate("portal")}><GraduationCap size={18} />Meu portal</button>}</nav><Link href="/sobre" className="site-link">Conheça o SIESCO <ArrowRight size={15} /></Link><div className="sidebar-footer"><span className="demo-dot" />Demonstração local<span>v0.1</span></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb"><button className="mobile-menu" aria-label="Abrir menu" onClick={() => setMobile(true)}><Menu size={22} /></button><span>Meu espaço</span><span>/</span><strong>{activeTitle}</strong></div><div className="topbar-user">{user.memberships.length > 1 && <select aria-label="Instituição ativa" value={tenant} onChange={e => { const selected = user.memberships.find(m => m.institution_id === e.target.value)!; setTenant(selected.institution_id); setView(["director", "coordinator", "secretary"].includes(selected.role) ? "dashboard" : "portal"); }} >{user.memberships.map(m => <option key={m.institution_id} value={m.institution_id}>{m.institution_name}</option>)}</select>}<span className="user-avatar">{user.name.slice(0, 1)}</span><div className="user-caption"><strong>{user.name}</strong><span>{roleName}</span></div><Button variant="ghost" size="icon" aria-label="Sair" onClick={logout}><LogOut size={18} /></Button></div></header>
      <main id="main" className="main-content">{error && <div className="error" role="alert">{error}</div>}{view === "dashboard" && manager ? <Dashboard key={tenant} base={base} name={user.name} role={role} navigate={navigate} /> : view === "whatsapp" && manager ? <WhatsAppDemo key={tenant} school={member?.institution_name || "Escola demonstrativa"} /> : view === "portal" ? <PersonalPortal key={tenant} base={base} name={user.name} /> : <CatalogView key={`${tenant}:${view}`} resource={view} base={base} role={role} expired={expired} />}</main>
    </div></div>;
}

function Login({ onLogin, initialError }: { onLogin: () => Promise<void>; initialError: string }) {
  const [email, setEmail] = useState("director@aurora.example.com");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await api("auth/login", { method: "POST", body: JSON.stringify({ email, password }) }); await onLogin(); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível entrar."); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-story"><div className="brand"><span className="brand-symbol"><GraduationCap size={26} /></span><div>siesco<span>PORTAL ESCOLAR</span></div></div><div><span className="banner-kicker">EDUCAÇÃO É CONEXÃO</span><h1>Mais perto de quem<br />faz a escola acontecer.</h1><p>Uma rotina organizada para cuidar do que importa: pessoas, ensino e novas possibilidades.</p><div className="login-illustration" aria-hidden="true"><div><School size={68} strokeWidth={1.2} /></div><span><BookOpen size={30} /></span><span><GraduationCap size={30} /></span></div></div><p className="login-story-footer">Gestão escolar com clareza e cuidado.</p></section><section className="login-form-wrap"><form className="login-form" onSubmit={submit}><span className="login-tag"><ShieldCheck size={15} /> SEU ESPAÇO ESCOLAR</span><h2>Bem-vindo de volta.</h2><p>Entre com sua conta para acessar o portal.</p><label className="field"><span>E-mail</span><input type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></label><label className="field"><span>Senha</span><input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>{error && <div className="error" role="alert">{error}</div>}<Button disabled={busy} type="submit" className="login-submit">{busy ? "Entrando…" : "Entrar no portal"}<ArrowRight size={18} /></Button><div className="login-demo"><Link href="/sobre" className="site-link">Conheça o SIESCO <ArrowRight size={15} /></Link><p>Ambiente local com dados fictícios. Use uma conta de demonstração e a senha configurada no arquivo .env.</p></div></form><p className="login-bottom">Siesco · Portal escolar</p></section></main>;
}

function PersonalPortal({ base, name }: { base: string; name: string }) {
  const [data, setData] = useState<{ students: { id: string; name: string }[]; message: string } | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => { let active = true; setError(""); api<NonNullable<typeof data>>(`${base}/portal`).then(d => { if (active) setData(d); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, [base, revision]);
  return <><div className="page-heading"><div><div className="eyebrow">MEU PORTAL</div><h1>Olá, {name.split(" · ")[0]}.</h1><p>Consulte os alunos associados ao seu acesso.</p></div></div>{error && <div className="error" role="alert">{error}<Button onClick={() => setRevision(n => n + 1)}>Tentar novamente</Button></div>}<section className="panel"><div className="panel-heading"><h2>Vínculos escolares</h2></div><div className="portal-cards">{!data ? <p role="status">Carregando vínculos…</p> : data.students.length ? data.students.map(s => <div className="portal-card" key={s.id}><GraduationCap size={26} /><strong>{s.name}</strong><span className="badge green">Vínculo ativo</span></div>) : <p>Nenhum vínculo disponível. Consulte a secretaria da escola.</p>}</div><p className="portal-note">{data?.message}</p></section></>;
}
