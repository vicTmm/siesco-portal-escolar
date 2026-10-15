"use client";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { KeyRound, ArrowRight, BookOpen, Building2, GraduationCap, LogOut, Menu, School, ShieldCheck, X } from "lucide-react";
import { api, selectMembership, type User } from "@/lib/api";
import { roles } from "@/lib/catalogs";
import { moduleIcons } from "@/lib/icons";
import { Button } from "./ui/button";
import { CatalogView } from "./catalog";
import { Dashboard } from "./dashboard";
import { WhatsAppDemo } from "./whatsapp";
import { LearningView, ReportView } from "./learning";
import { AccessForm, MfaSettings } from "./access";
import { ManagementView } from "./management";
import { AnnualView } from "./annual";

import {clearOffline,offlineIdentity} from "@/lib/offline-store";
import {ExamsView} from "./exams";
import {NotificationsView} from "./notifications";
import {AccessControlView} from "./access-control";
import {CommerceView} from "./commerce";
import { InsightsView } from "./insights";
import { ServicesView, MeetingsView } from "./services";
import { CommunityView, DocumentsView } from "./community";

const NotificationIcon=moduleIcons.notifications;
const AccessIcon=moduleIcons["access-control"];
const navigation = [
  {key:"notifications",title:"Notificações",icon:moduleIcons.notifications},
  { key: "search", title: "Busca global", icon: moduleIcons["search"], group: "PRINCIPAL" },
  { key: "dashboard", title: "Visão geral", icon: moduleIcons["dashboard"] },
  { key: "students", title: "Alunos", icon: moduleIcons["students"], group: "PESSOAS" },
  { key: "guardians", title: "Responsáveis", icon: moduleIcons["guardians"] },
  { key: "guardian-links", title: "Vínculos familiares", icon: moduleIcons["guardian-links"] },
  { key: "teachers", title: "Professores", icon: moduleIcons["teachers"] },
  { key: "academic-years", title: "Anos letivos", icon: moduleIcons["academic-years"], group: "ACADÊMICO" },
  { key: "academic-terms", title: "Períodos letivos", icon: moduleIcons["academic-terms"] },
  { key: "subjects", title: "Disciplinas", icon: moduleIcons["subjects"] },
  { key: "curricula", title: "Currículos", icon: moduleIcons["curricula"] },
  { key: "curriculum-subjects", title: "Matriz curricular", icon: moduleIcons["curriculum-subjects"] },
  { key: "classes", title: "Turmas", icon: moduleIcons["classes"] },
  { key: "assignments", title: "Atribuições docentes", icon: moduleIcons["assignments"] },
  { key: "enrollments", title: "Matrículas", icon: moduleIcons["enrollments"] },
  { key: "offline", title: "Diário offline", icon: moduleIcons.offline },
  { key: "learning", title: "Diário e avaliações", icon: moduleIcons["learning"], group: "PEDAGÓGICO" },
  { key: "annual", title: "Consolidação anual", icon: moduleIcons["annual"] },
  { key: "alerts", title: "Alertas pedagógicos", icon: moduleIcons.alerts },
  {key:"exams",title:"Provas e gabaritos",icon:moduleIcons.exams},
  { key: "correction", title: "Correção por gabarito", icon: moduleIcons.correction },
  { key: "timetables", title: "Grade de horários", icon: moduleIcons.timetables },
  { key: "notices", title: "Mural e autorizações", icon: moduleIcons.notices, group: "COMUNICAÇÃO" },
  { key: "meetings", title: "Agenda de reuniões", icon: moduleIcons.meetings },
  { key: "whatsapp", title: "Avisos por WhatsApp", icon: moduleIcons["whatsapp"] },
  { key: "documents", title: "Documentos escolares", icon: moduleIcons.documents, group: "SECRETARIA" },
  { key: "exports", title: "Relatórios", icon: moduleIcons["exports"] },
  { key: "audit", title: "Auditoria", icon: moduleIcons["audit"], group: "ADMINISTRAÇÃO" },
  { key: "accounts", title: "Contas e permissões", icon: moduleIcons["accounts"] },
  { key: "units", title: "Unidades escolares", icon: moduleIcons.units },
  {key:"access-control",title:"Identificação e saída",icon:moduleIcons["access-control"]},
  { key: "commerce", title:"Carteira, cantina e loja", icon:moduleIcons.commerce },
  { key: "services", title: "Serviços escolares", icon: moduleIcons.services, group: "OPERAÇÕES" },
];

export function Portal() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [resetToken, setResetToken] = useState("");
  useEffect(() => { setResetToken(new URLSearchParams(window.location.hash.slice(1)).get("reset_token") || ""); }, []);
  const [tenant, setTenant] = useState("");
  const [view, setView] = useState("dashboard");
  const [serviceDefault,setServiceDefault]=useState("");
  const [notificationCount,setNotificationCount]=useState(0);
  const [mobile, setMobile] = useState(false);
  const [error, setError] = useState("");
  const expired = useCallback(() => { setUser(null); setTenant(""); selectMembership(""); sessionStorage.setItem("siesco_offline_lock","1"); }, []);
  const loadUser = useCallback(async () => {
    const next = await api<User>("me");
    const first=next.memberships.find(m=>m.id===sessionStorage.getItem("siesco_active_membership"))||next.memberships[0];
    if(first)await offlineIdentity(next.id,first.id).catch(()=>{});else await clearOffline().catch(()=>{});
    selectMembership(first?.id||"");
    setTenant(first?.id||"");setUser(next);setError("");
    setView(next.platform_admin ? "institutions" : ["director", "secretary", "coordinator"].includes(first?.role) ? "dashboard" : "portal");
  }, []);
  useEffect(() => { loadUser().catch(e => { if (e.status !== 401) setError(e.message); }).finally(() => setReady(true)); }, [loadUser]);
  function navigate(next: string) { if(next.startsWith("services:")){setServiceDefault(next.split(":")[1]);setView("services");setMobile(false);return;}if(next==="services")setServiceDefault(""); if(next==="offline"){window.location.assign("/offline");return;} setView(next); setMobile(false); }
  async function logout() { try { await api("auth/logout", { method: "POST" }); await clearOffline().catch(()=>{}); expired(); } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível sair."); } }
  useEffect(()=>{
    const active=user?.memberships.find(m=>m.id===tenant);if(!active)return;
    const update=()=>api<{count:number}>(`institutions/${active.institution_id}/notifications?limit=1`).then(n=>setNotificationCount(n.count)).catch(()=>setNotificationCount(0));
    void update();const timer=setInterval(()=>{if(!document.hidden)void update();},30000);return()=>clearInterval(timer);
  },[user,tenant]);
  if (!ready) return <main className="fatal" role="status">Abrindo seu espaço escolar…</main>;
  if (resetToken) return <main className="login-form-wrap"><AccessForm mode="reset" token={resetToken} onBack={() => { window.history.replaceState(null, "", "/"); setResetToken(""); expired(); }} /></main>;
  if (!user) return <Login onLogin={loadUser} initialError={error} />;
  const member = user.memberships.find(m => m.id === tenant);
  const role = user.platform_admin && view === "institutions" ? "platform" : member?.role || "";
  const manager = ["director", "secretary", "coordinator"].includes(role);
  const base = `institutions/${member?.institution_id || ""}`;
  const roleName = role === "platform" ? "Administração da plataforma" : roles.find(r => r[0] === role)?.[1] || "Sem vínculo ativo";
  const activeTitle = view === "password" ? "Minha senha" : view === "institutions" ? "Instituições" : view === "portal" ? "Meu portal" : navigation.find(n => n.key === view)?.title;
  return <div className="app-shell"><a href="#main" className="skip-link">Pular para conteúdo</a>{mobile && <button className="mobile-scrim" aria-label="Fechar menu" onClick={() => setMobile(false)} />}
    <aside className={`sidebar ${mobile ? "is-open" : ""}`}><div className="brand"><span className="brand-symbol"><GraduationCap size={24} /></span><div>siesco<span>PORTAL ESCOLAR</span></div><button className="mobile-close" aria-label="Fechar menu" onClick={() => setMobile(false)}><X size={20} /></button></div><div className="institution-label"><span className="school-symbol"><Building2 size={19} /></span><div><strong>{member?.institution_name || "Plataforma Siesco"}</strong><span>{member ? member.school_name : "Gestão de instituições"}</span></div></div>
      <nav aria-label="Menu principal">{user.platform_admin ? <button onClick={() => navigate("institutions")} className="nav-link active"><Building2 size={18} />Instituições</button> : manager ? navigation.filter(n => (!["accounts", "audit", "units"].includes(n.key) || role === "director") && (n.key !== "exports" || role !== "coordinator") && (!["offline","exams"].includes(n.key) || role!=="secretary") && (!["commerce","access-control"].includes(n.key) || role!=="coordinator")).map(item => <div key={item.key}>{item.group && <div className="nav-group">{item.group}</div>}<button aria-current={view === item.key ? "page" : undefined} className={`nav-link ${view === item.key ? "active" : ""}`} onClick={() => navigate(item.key)}><item.icon size={18} />{item.title}{view === item.key && <span className="active-dot" />}</button></div>) : <><button className={`nav-link ${view === "portal" ? "active" : ""}`} onClick={() => navigate("portal")}><moduleIcons.portal size={18} />Meu portal</button>{role === "teacher" && <button className={`nav-link ${view === "learning" ? "active" : ""}`} onClick={() => navigate("learning")}><moduleIcons.learning size={18} />Diário e avaliações</button>}{role === "teacher"&&<button className="nav-link" onClick={()=>navigate("offline")}><moduleIcons.offline size={18}/>Diário offline</button>}{role === "teacher"&&<button className="nav-link" onClick={()=>navigate("correction")}><moduleIcons.correction size={18}/>Correção por gabarito</button>}{role==="teacher"&&<button className="nav-link" onClick={()=>navigate("exams")}><moduleIcons.exams size={18}/>Provas e gabaritos</button>}{<><button className="nav-link" onClick={()=>navigate("services")}><moduleIcons.services size={18}/>Serviços escolares</button>{role!=="student"&&<button className="nav-link" onClick={()=>navigate("meetings")}><moduleIcons.meetings size={18}/>Agenda de reuniões</button>}</>}<button className="nav-link" onClick={()=>navigate("notices")}><moduleIcons.notices size={18}/>Mural e autorizações</button>{role!=="teacher"&&<button className="nav-link" onClick={()=>navigate("documents")}><moduleIcons.documents size={18}/>Documentos escolares</button>}{["guardian","student"].includes(role)&&<button className="nav-link" onClick={()=>navigate("commerce")}><moduleIcons.commerce size={18}/>Carteira, cantina e loja</button>}{["guardian","student"].includes(role)&&<button className="nav-link" onClick={()=>navigate("access-control")}><AccessIcon size={18}/>Identificação e saída</button>}</>}</nav><Link href="/sobre" className="site-link">Conheça o SIESCO <ArrowRight size={15} /></Link><div className="sidebar-footer"><span className="demo-dot" />Demonstração local<span>v0.1</span></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb"><button className="mobile-menu" aria-label="Abrir menu" onClick={() => setMobile(true)}><Menu size={22} /></button><span>Meu espaço</span><span>/</span><strong>{activeTitle}</strong></div><div className="topbar-user">{user.memberships.length > 1 && <select aria-label="Instituição ativa" value={tenant} onChange={e => { const selected = user.memberships.find(m => m.id === e.target.value)!; setTenant(selected.id); selectMembership(selected.id); setView(["director", "coordinator", "secretary"].includes(selected.role) ? "dashboard" : "portal"); }} >{user.memberships.map(m => <option key={m.id} value={m.id}>{m.institution_name} · {m.school_name} · {roles.find(r=>r[0]===m.role)?.[1]||m.role}</option>)}</select>}<span className="user-avatar">{user.name.slice(0, 1)}</span><div className="user-caption"><strong>{user.name}</strong><span>{roleName}</span></div>{member&&<Button variant="ghost" aria-label="Notificações" onClick={()=>navigate("notifications")}><NotificationIcon size={18}/>{notificationCount>0&&<span>{notificationCount}</span>}</Button>}<Button variant="ghost" size="sm" className="topbar-password" aria-label="Minha senha" onClick={() => navigate("password")}><KeyRound size={18}/><span>Minha senha</span></Button><Button variant="ghost" size="icon" aria-label="Sair" onClick={logout}><LogOut size={18} /></Button></div></header>
      <main id="main" className="main-content">{error && <div className="error" role="alert">{error}</div>}{view==="exams"?<ExamsView key={tenant} base={base}/>:view==="notifications"?<NotificationsView key={tenant} base={base} navigate={navigate}/>:view==="access-control"?<AccessControlView key={tenant} base={base} role={role}/>:view==="commerce"?<CommerceView key={tenant} base={base} role={role}/>: ["alerts","timetables","correction","units"].includes(view) ? <InsightsView key={`${tenant}:${view}`} base={base} mode={view} role={role}/> : view === "services" ? <ServicesView key={`${tenant}:${serviceDefault}`} base={base} role={role} initialModule={serviceDefault}/> : view === "meetings" ? <MeetingsView key={tenant} base={base} role={role}/> : view === "notices" ? <CommunityView key={tenant} base={base} role={role}/> : view === "documents" ? <DocumentsView key={tenant} base={base} role={role}/> : view === "annual" && manager ? <AnnualView key={tenant} base={base} role={role} /> : view === "password" ? <><AccessForm mode="change" onBack={() => navigate(user.platform_admin ? "institutions" : manager ? "dashboard" : "portal")} onChanged={expired} /><MfaSettings onChanged={expired} /></> : ["search", "audit", "exports"].includes(view) && manager ? <ManagementView key={`${tenant}:${view}`} base={base} mode={view as "search" | "audit" | "exports"} navigate={navigate} /> : view === "learning" && (manager || role === "teacher") ? <LearningView key={tenant} base={base} role={role} /> : view === "dashboard" && manager ? <Dashboard key={tenant} base={base} name={user.name} role={role} navigate={navigate} /> : view === "whatsapp" && manager ? <WhatsAppDemo key={tenant} school={member?.institution_name || "Escola demonstrativa"} /> : view === "portal" ? <PersonalPortal key={tenant} base={base} name={user.name} role={role} /> : <CatalogView key={`${tenant}:${view}`} resource={view} base={base} role={role} expired={expired} />}</main>
    </div></div>;
}

function Login({ onLogin, initialError }: { onLogin: () => Promise<void>; initialError: string }) {
  const [access, setAccess] = useState<"forgot" | "reset" | null>(null);
  const [email, setEmail] = useState("director@aurora.example.com");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await api("auth/login", { method: "POST", body: JSON.stringify({ email, password, otp }) }); await onLogin(); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível entrar."); }
    finally { setBusy(false); }
  }
  if (access) return <main className="login-form-wrap"><AccessForm mode={access} token={new URLSearchParams(window.location.search).get("reset_token") || ""} onBack={() => { window.history.replaceState(null, "", "/"); setAccess(null); }} /></main>;
  return <main className="login-page"><section className="login-story"><div className="brand"><span className="brand-symbol"><GraduationCap size={26} /></span><div>siesco<span>PORTAL ESCOLAR</span></div></div><div><span className="banner-kicker">EDUCAÇÃO É CONEXÃO</span><h1>Mais perto de quem<br />faz a escola acontecer.</h1><p>Uma rotina organizada para cuidar do que importa: pessoas, ensino e novas possibilidades.</p><div className="login-illustration" aria-hidden="true"><div><School size={68} strokeWidth={1.2} /></div><span><BookOpen size={30} /></span><span><GraduationCap size={30} /></span></div></div><p className="login-story-footer">Gestão escolar com clareza e cuidado.</p></section><section className="login-form-wrap"><form className="login-form" onSubmit={submit}><span className="login-tag"><ShieldCheck size={15} /> SEU ESPAÇO ESCOLAR</span><h2>Bem-vindo de volta.</h2><p>Entre com sua conta para acessar o portal.</p><label className="field"><span>E-mail</span><input type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></label><label className="field"><span>Senha</span><input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label><label className="field"><span>Código de verificação (se ativado)</span><input autoComplete="one-time-code" value={otp} onChange={e => setOtp(e.target.value)} /></label>{error && <div className="error" role="alert">{error}</div>}<Button disabled={busy} type="submit" className="login-submit">{busy ? "Entrando…" : "Entrar no portal"}<ArrowRight size={18} /></Button><Button type="button" variant="ghost" onClick={() => setAccess("forgot")}>Esqueci minha senha</Button><div className="login-demo"><Link href="/sobre" className="site-link">Conheça o SIESCO <ArrowRight size={15} /></Link><p>Ambiente local com dados fictícios. Use uma conta de demonstração e a senha configurada no arquivo .env.</p></div></form><p className="login-bottom">Siesco · Portal escolar</p></section></main>;
}

function PersonalPortal({ base, name, role }: { base: string; name: string; role: string }) {
  const [data, setData] = useState<{ students: { id: string; name: string }[]; message: string } | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [student, setStudent] = useState("");
  useEffect(() => { let active = true; setError(""); api<NonNullable<typeof data>>(`${base}/portal?limit=50&offset=${page * 50}&q=${encodeURIComponent(search)}`).then(d => { if (active) setData(d); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, [base, revision, page, search]);
  if (student) return <ReportView base={base} student={student} onBack={() => setStudent("")} />;
  return <><div className="page-heading"><div><div className="eyebrow">MEU PORTAL</div><h1>Olá, {name.split(" · ")[0]}.</h1><p>Consulte os alunos associados ao seu acesso.</p></div></div>{error && <div className="error" role="alert">{error}<Button onClick={() => setRevision(n => n + 1)}>Tentar novamente</Button></div>}<section className="panel"><div className="panel-heading"><h2>Vínculos escolares</h2></div><label className="field learning-body"><span>Buscar aluno vinculado</span><input value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} /></label><div className="portal-cards">{!data ? <p role="status">Carregando vínculos…</p> : data.students.length ? data.students.map(s => <div className="portal-card" key={s.id}><GraduationCap size={26} /><strong>{s.name}</strong><span className="badge green">Vínculo ativo</span>{role !== "teacher" && <Button variant="outline" onClick={() => setStudent(s.id)}>Ver boletim</Button>}</div>) : <p>Nenhum vínculo disponível. Consulte a secretaria da escola.</p>}</div><p className="portal-note">{data?.message}</p><div className="table-footer"><Button variant="ghost" disabled={page === 0} onClick={() => setPage(n => n - 1)}>Anterior</Button><span>Página {page + 1}</span><Button variant="ghost" disabled={!data || data.students.length < 50} onClick={() => setPage(n => n + 1)}>Próxima</Button></div></section></>;
}
