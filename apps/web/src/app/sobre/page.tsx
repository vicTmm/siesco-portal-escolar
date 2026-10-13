import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check, GraduationCap, Globe2, Laptop, ShieldCheck, Smartphone, Users, BookOpen, ClipboardList } from "lucide-react";
import styles from "./site.module.css";

export const metadata: Metadata = {
  title: "SIESCO · Sua escola, sempre por perto",
  description: "Conheça o SIESCO: gestão escolar que conecta pessoas, organiza a rotina e coloca o acesso online no centro da experiência.",
};

const resources = [
  { icon: Users, number: "01", title: "Pessoas conectadas", text: "Alunos, responsáveis e professores organizados no mesmo lugar. Vínculos familiares e acessos de acordo com o papel de cada pessoa." },
  { icon: BookOpen, number: "02", title: "Uma rotina organizada", text: "Disciplinas, turmas e atribuições docentes para dar clareza à organização da escola, do cadastro à matrícula." },
  { icon: ClipboardList, number: "03", title: "Gestão com visibilidade", text: "Dashboard com indicadores de cadastros e ocupação das turmas. Informações que ajudam a acompanhar o dia a dia." },
];

export default function AboutPage() {
  return <div className={styles.site}>
    <a className="skip-link" href="#conteudo">Pular para conteúdo</a>
    <header className={styles.header}>
      <Link href="/sobre" className={styles.brand} aria-label="SIESCO — início do site"><GraduationCap size={30} /><span>siesco<small>PORTAL ESCOLAR</small></span></Link>
      <nav aria-label="Navegação do site"><a href="#recursos">O SIESCO</a><a href="#acesso">Acesso online</a><Link href="/" className={styles.smallCta}>Entrar no app <ArrowRight size={16} /></Link></nav>
    </header>

    <main id="conteudo">
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}><span /> MAIS CONEXÃO. MAIS ESCOLA.</p>
          <h1 id="hero-title">Sua escola,<br />sempre <em>por perto.</em></h1>
          <p className={styles.intro}>Pessoas, informações e rotina escolar em um só lugar. Conheça o SIESCO e abra espaço para o que mais importa: ensinar e aprender.</p>
          <div className={styles.actions}><Link href="/" className={styles.primary}>Acessar o portal <ArrowRight size={18} /></Link><a href="#recursos" className={styles.textLink}>Conheça o SIESCO <span>↗</span></a></div>
          <div className={styles.heroNote}><ShieldCheck size={17} /> Cada pessoa com acesso às informações do seu perfil.</div>
        </div>
        <div className={styles.visual}>
          <div className={styles.orbit} aria-hidden="true" />
          <div className={styles.preview}>
            <div className={styles.previewBar}><span><GraduationCap size={21} /> siesco</span><span className={styles.example}>VISÃO ILUSTRATIVA</span></div>
            <div className={styles.previewBody}><p>SEU ESPAÇO ESCOLAR</p><h2>Uma escola.<br />Muitas conexões.</h2>
              <div className={styles.previewTiles}><div><Users size={22} /><strong>Pessoas</strong><span>Uma comunidade</span></div><div><BookOpen size={22} /><strong>Turmas</strong><span>Mais organização</span></div></div>
              <div className={styles.previewRow}><span><Check size={16} /></span><div><strong>Informação no lugar certo</strong><p>Da secretaria à família.</p></div><ArrowRight size={17} /></div>
            </div>
          </div>
          <div className={styles.phone}><Smartphone size={23} /><span>A escola vai<br /><strong>com você.</strong></span><div><span /><span /><span /></div><small>NO SEU RITMO</small></div>
          <div className={styles.onlineTag}><Globe2 size={18} /> Feito para conectar</div>
        </div>
      </section>

      <section id="acesso" className={styles.access} aria-labelledby="access-title">
        <div><p className={styles.eyebrow}>SEM LIMITES DE LUGAR OU HORÁRIO</p><h2 id="access-title">Acesso online.<br />A escola além dos muros.</h2><p>A proposta do SIESCO é simples: todos os dados da sua escola acessíveis de qualquer lugar, em qualquer dispositivo, 24 horas por dia, 7 dias por semana — sempre respeitando as permissões de cada usuário.</p><p className={styles.accessNote}>No computador, tablet ou celular, com conexão à internet.</p></div>
        <div className={styles.availability}><strong>24<span>/</span>7</strong><p>Seu tempo. Seu lugar. Sua escola.</p><div><Laptop size={27} /><span /><Smartphone size={23} /><Globe2 size={26} /></div></div>
      </section>

      <section id="recursos" className={styles.resources} aria-labelledby="resources-title">
        <div className={styles.sectionHeading}><p className={styles.eyebrow}>MENOS DISPERSÃO, MAIS CLAREZA</p><h2 id="resources-title">O dia a dia da escola<br />encontra o seu lugar.</h2><p>Uma base comum para organizar a gestão e aproximar quem faz parte da escola.</p></div>
        <div className={styles.resourceGrid}>{resources.map(({ icon: Icon, number, title, text }) => <article key={number}><div><Icon size={26} /><span>{number}</span></div><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className={styles.people} aria-labelledby="people-title"><div><p className={styles.eyebrow}>UMA ESCOLA, DIFERENTES OLHARES</p><h2 id="people-title">Cada pessoa tem<br />seu espaço.</h2></div><dl><div><dt>Gestão e secretaria</dt><dd>Cadastros, organização de turmas e matrículas em uma rotina compartilhada.</dd></div><div><dt>Professores</dt><dd>Acesso aos alunos associados às turmas sob sua responsabilidade.</dd></div><div><dt>Alunos e responsáveis</dt><dd>Um portal com os vínculos escolares autorizados para cada conta.</dd></div></dl></section>

      <section className={styles.closing}><p className={styles.eyebrow}>BEM-VINDO AO SIESCO</p><h2>Mais perto da sua escola.<br />A um acesso de distância.</h2><Link href="/" className={styles.primary}>Entrar no app <ArrowRight size={18} /></Link><p className={styles.stage}>O SIESCO está em evolução. A versão atual é de demonstração; a disponibilidade online 24/7 é um requisito para a operação em produção.</p></section>
    </main>
    <footer className={styles.footer}><Link href="/sobre" className={styles.brand}><GraduationCap size={25} /><span>siesco</span></Link><p>Conexões que fazem a escola acontecer.</p><Link href="/">Voltar para o app <ArrowRight size={15} /></Link></footer>
  </div>;
}
