"use client";

import { useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, MessageCircle, Send } from "lucide-react";
import { Button } from "./ui/button";
import { moduleIcons } from "@/lib/icons";

const money = (value: number) => value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const classes = Array.from({ length: 10 }, (_, i) => ({ id: String(i), name: `${Math.floor(i / 2) + 1}º ano ${i % 2 ? "B" : "A"}`, shift: i % 2 ? "Tarde" : "Manhã" }));
const names = ["Ana", "Bruno", "Carolina", "Daniel", "Elisa", "Felipe", "Gabriela", "Henrique", "Isabela", "João"];
const recipients = Array.from({ length: 350 }, (_, i) => ({ id: i, name: `${names[i % 10]} · Família ${String(i + 1).padStart(3, "0")}`, student: `Aluno demonstrativo ${String(i + 1).padStart(3, "0")}`, classId: String(Math.floor(i / 35)) }));
const models = {
  schedule: { label: "Alteração de horário", text: "Informamos uma alteração no horário das aulas. Amanhã, a entrada será às 8h. Agradecemos a compreensão." },
  meeting: { label: "Lembrete de reunião", text: "Lembramos que nossa reunião de responsáveis será na sexta-feira, às 18h, na escola. Contamos com sua presença." },
  notice: { label: "Comunicado escolar", text: "Na próxima segunda-feira não haverá aula. Retomaremos nossas atividades na terça-feira, no horário habitual." },
};
type History = { id: number; title: string; count: number; cost: number; time: string };

export function WhatsAppDemo({ school }: { school: string }) {
  const [step, setStep] = useState(0);
  const [shift, setShift] = useState("Todos");
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [excluded, setExcluded] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [model, setModel] = useState<keyof typeof models>("schedule");
  const [text, setText] = useState<string>(models.schedule.text);
  const [category, setCategory] = useState("utility");
  const [confirmed, setConfirmed] = useState(false);
  const [history, setHistory] = useState<History[]>([]);
  const [receipt, setReceipt] = useState<History | null>(null);
  const availableClasses = classes.filter(c => shift === "Todos" || c.shift === shift);
  const audience = recipients.filter(r => availableClasses.some(c => c.id === r.classId) && (!selectedClasses.length || selectedClasses.includes(r.classId)));
  const selected = audience.filter(r => !excluded.includes(r.id));
  const visible = audience.filter(r => `${r.name} ${r.student}`.toLowerCase().includes(search.toLowerCase()));
  const rate = category === "utility" ? 0.035 : 0.3217;
  const cost = selected.length * rate;
  const preview = `Olá, ${selected[0]?.name.split(" · ")[0] || "responsável"}!\n\n${text.trim()}\n\n${school}`;
  function simulate() {
    if (!confirmed || !text.trim() || !selected.length) return;
    const item = { id: Date.now(), title: models[model].label, count: selected.length, cost, time: new Date().toLocaleString("pt-BR") };
    setHistory(items => [item, ...items]); setReceipt(item); setStep(3);
  }
  function restart() { setStep(0); setConfirmed(false); setReceipt(null); }
  return <div className="wa-demo">
    <div className="page-heading"><div><div className="eyebrow">COMUNICAÇÃO COM AS FAMÍLIAS</div><h1>Avisos por WhatsApp</h1><p>Uma mensagem, cada família. Selecione quem recebe e acompanhe seu comunicado.</p></div><span className="badge green"><MessageCircle size={14} /> Demonstração</span></div>
    <div className="wa-notice"><strong>Modo demonstrativo</strong><span>Dados fictícios de 350 alunos. Nenhuma mensagem será enviada e nenhum valor será cobrado.</span></div>
    <ol className="wa-steps" aria-label="Etapas do envio">{["Destinatários", "Mensagem", "Revisão"].map((label, i) => <li key={label} aria-current={step === i ? "step" : undefined} className={step >= i ? "current" : ""}><span>{step > i ? <CheckCircle2 size={17} /> : i + 1}</span>{label}</li>)}</ol>
    {step === 3 && receipt ? <section className="panel wa-success" role="status"><CheckCircle2 size={46} /><h2>Simulação concluída!</h2><p>O aviso foi marcado como entregue para {receipt.count} responsáveis fictícios.</p><p>Custo simulado: <strong>{money(receipt.cost)}</strong>. Nenhum envio real foi realizado.</p><Button onClick={restart}>Criar outro aviso <ArrowRight size={16} /></Button></section> : <div className="wa-layout"><section className="panel wa-editor">
      {step === 0 && <><h2>Quem vai receber?</h2><p className="wa-muted">Um responsável por aluno, com autorização de recebimento simulada.</p><label className="field"><span>Turno</span><select value={shift} onChange={e => { setShift(e.target.value); setSelectedClasses([]); setExcluded([]); }}><option>Todos</option><option>Manhã</option><option>Tarde</option></select></label><fieldset className="wa-class-picker"><legend>Turmas</legend><label><input type="checkbox" checked={!selectedClasses.length} onChange={() => { setSelectedClasses([]); setExcluded([]); }} /> Todas as turmas do turno</label><div>{availableClasses.map(c => <label key={c.id}><input type="checkbox" checked={selectedClasses.includes(c.id)} onChange={() => { setSelectedClasses(current => current.includes(c.id) ? current.filter(id => id !== c.id) : [...current, c.id]); setExcluded([]); }} />{c.name}<small>{c.shift} · 35 alunos</small></label>)}</div></fieldset><p className="wa-muted">Sem uma turma específica selecionada, todas as turmas do turno estão incluídas.</p><div className="wa-recipient-heading"><h3>Responsáveis ({selected.length})</h3><Button variant="ghost" size="sm" onClick={() => setExcluded([])}>Selecionar todos</Button></div><label className="field"><span>Buscar responsável ou aluno</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Digite um nome" /></label><div className="wa-recipients">{visible.map(r => <label key={r.id}><input type="checkbox" checked={!excluded.includes(r.id)} onChange={() => setExcluded(ids => ids.includes(r.id) ? ids.filter(id => id !== r.id) : [...ids, r.id])} /><span><strong>{r.name}</strong><small>{r.student} · {classes[Number(r.classId)].name} · {classes[Number(r.classId)].shift}</small></span><span className="badge green">Autorizado</span></label>)}{!visible.length && <p className="wa-muted">Nenhum responsável encontrado.</p>}</div></>}
      {step === 1 && <><h2>Prepare o comunicado</h2><p className="wa-muted">Escolha um exemplo e escreva o aviso uma única vez.</p><label className="field"><span>Modelo de mensagem</span><select value={model} onChange={e => { const value = e.target.value as keyof typeof models; setModel(value); setText(models[value].text); }} >{Object.entries(models).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}</select></label><label className="field"><span>Texto do aviso</span><textarea aria-label="Texto do aviso" rows={8} maxLength={800} value={text} onChange={e => setText(e.target.value)} placeholder="Escreva seu comunicado…" /><small>{text.length}/800 caracteres</small></label><label className="field"><span>Categoria para simular o custo</span><select value={category} onChange={e => setCategory(e.target.value)}><option value="utility">Utilidade · R$ 0,0350 por mensagem</option><option value="marketing">Marketing · R$ 0,3217 por mensagem</option></select></label><div className="wa-notice">Os modelos e a edição livre são ilustrativos. No envio real, o conteúdo deve seguir um modelo aprovado pela Meta, que também define sua categoria.</div></>}
      {step === 2 && <><h2>Confira antes de enviar</h2><p className="wa-muted">Cada responsável receberia o aviso em uma conversa individual.</p><dl className="wa-summary"><div><dt>Turno</dt><dd>{shift}</dd></div><div><dt>Turmas</dt><dd>{selectedClasses.length ? availableClasses.filter(c => selectedClasses.includes(c.id)).map(c => c.name).join(", ") : "Todas do turno selecionado"}</dd></div><div><dt>Responsáveis selecionados</dt><dd>{selected.length}</dd></div><div><dt>Modelo</dt><dd>{models[model].label}</dd></div><div><dt>Categoria simulada</dt><dd>{category === "utility" ? "Utilidade" : "Marketing"}</dd></div><div><dt>Custo estimado deste aviso</dt><dd>{money(cost)}</dd></div></dl><label className="wa-consent"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Conferi a mensagem e os destinatários. Quero simular este envio.</label></>}
      <div className="wa-actions">{step > 0 && <Button variant="outline" onClick={() => { setStep(step - 1); setConfirmed(false); }}><ArrowLeft size={16} /> Voltar</Button>}{step < 2 ? <Button disabled={!selected.length || (step === 1 && !text.trim())} onClick={() => setStep(step + 1)}>Continuar <ArrowRight size={16} /></Button> : <Button disabled={!confirmed} onClick={simulate}><Send size={16} /> Simular envio</Button>}</div>
    </section><aside className="wa-preview"><section className="panel wa-cost"><moduleIcons.guardians size={22} /><span>Destinatários selecionados</span><strong>{selected.length}</strong><div><span>Este aviso</span><b>{money(cost)}</b></div><div><span>15 avisos com este público</span><b>{money(cost * 15)}/mês</b></div><p>Estimativa ilustrativa, sem impostos ou taxas adicionais. A tarifa e a categoria precisam ser confirmadas na ativação.</p></section><section className="wa-phone"><div className="wa-phone-header"><MessageCircle size={22} /><div><strong>{school}</strong><small>Prévia da conversa individual</small></div></div><div className="wa-bubble">{preview}<small>09:41 ✓✓</small></div><p>Exemplo para {selected[0]?.name || "um responsável"}. Dados fictícios.</p></section></aside></div>}
    <section className="panel wa-history"><div className="panel-heading"><div><h2>Histórico de simulações</h2><p>Disponível enquanto esta tela estiver aberta.</p></div><span className="badge neutral">{history.length} avisos</span></div>{history.length ? <div className="table-scroll"><table><thead><tr><th>Aviso / data</th><th>Responsáveis</th><th>Custo simulado</th><th>Situação</th></tr></thead><tbody>{history.map(item => <tr key={item.id}><td><strong>{item.title}</strong><br />{item.time}</td><td>{item.count}</td><td>{money(item.cost)}</td><td><span className="badge green">Entregue · simulado</span></td></tr>)}</tbody></table></div> : <div className="wa-empty"><MessageCircle size={24} /><p>Seu primeiro aviso começa aqui.</p><small>Conclua o fluxo acima para visualizar o resultado simulado.</small></div>}</section>
  </div>;
}
