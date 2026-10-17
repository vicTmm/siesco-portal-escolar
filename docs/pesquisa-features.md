> Status de implementação: consulte [expansao-pesquisa.md](expansao-pesquisa.md). Esta pesquisa inclui visão futura e não representa uma lista de funcionalidades integralmente concluídas.

# Pesquisa Aprofundada: Funcionalidades, Inovações e Tendências em Apps de Gestão Escolar (2024–2026)

Este documento apresenta um levantamento exaustivo do ecossistema de software de gestão escolar (Sistemas de Gestão Escolar - SGE, Student Information Systems - SIS e SuperApps Escolares). O objetivo é fornecer uma base completa e estruturada para **cruzamento e análise de viabilidade com o SIESCO Portal Escolar**.

---

## 1. Visão Geral e Mudança de Paradigma do Mercado

O mercado de tecnologia educacional (EdTech) passou por uma transformação radical nos últimos anos. Os softwares deixaram de ser meros "bancos de dados de notas e cadastros administrativos em servidores locais" para se tornarem **ecossistemas integrados em nuvem (SuperApps All-in-One)**.

### Os Três Grandes Motores da Transformação Atual:
1. **Centralização All-in-One:** Escolas rejeitam a fragmentação (um app para recados, um ERP antigo para financeiro, planilhas para notas e catraca física isolada). O padrão exigido hoje é um portal único que sincronize secretaria, pedagógico, financeiro, segurança e famílias.
2. **IA Generativa e Preditiva como Infraestrutura:** A IA deixou de ser um recurso isolado para atuar como assistente de redação docente (pareceres, planos de aula BNCC), analista de risco (alerta precoce de evasão e defasagem) e assistente de atendimento às famílias 24/7.
3. **Segurança Física, Logística e ECA Digital/LGPD:** A integração de reconhecimento facial, gestão de portaria/saída inteligente e proteção rigorosa dos dados de menores (ECA Digital) tornaram-se requisitos de primeira ordem para pais e gestores.

---

## 2. Taxonomia Completa de Funcionalidades por Módulo

Abaixo está o mapeamento detalhado das funcionalidades existentes no estado da arte dos principais players nacionais (*Agenda Edu, ClipEscola, ClassApp/Meu Arco, Proesc, SophiA, Sponte, Didatiko*) e internacionais (*PowerSchool, Toddle, Alma SIS, Brightwheel*).

```
                            ┌───────────────────────────────────────────────┐
                            │           SUPERAPP ESCOLAR MODERNO            │
                            └──────────────────────┬────────────────────────┘
                                                   │
     ┌──────────────────┬──────────────────┬───────┴──────────┬──────────────────┬──────────────────┐
     ▼                  ▼                  ▼                  ▼                  ▼                  ▼
┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐
│ Família │        │Diário & │        │Inclusão │        │Segurança│        │Secretaria│       │Finanças │
│& Comun. │        │Pedagóg. │        │ & Saúde │        │& Portar.│        │& Matríc.│       │& Serviços│
└─────────┘        ┌─────────┘        └─────────┘        └─────────┘        └─────────┘        └─────────┘
```

---

### Módulo 1: Comunicação e Engajamento da Família (Family Engagement)

Substitui grupos informais de WhatsApp e agendas de papel por canais institucionais seguros e auditáveis.

* **Linha do Tempo / Feed de Notícias:** Publicação de avisos, fotos e vídeos de eventos escolares, com segmentação por escola, nível de ensino, turma ou aluno individual.
* **Mural de Momentos com Privacidade Rígida:** Compartilhamento de fotos e vídeos em alta resolução com filtro de consentimento de imagem (LGPD/ECA Digital) e visualização restrita à família do aluno.
* **Canais de Atendimento com Horário de Expediente:** Chat estruturado por departamentos (Secretaria, Coordenação, Financeiro, Psicologia) com horários pré-fixados de funcionamento para evitar invasão do tempo livre dos profissionais fora do horário escolar.
* **Métricas de Leitura e Confirmação:** Indicador em tempo real de quem abriu e leu cada comunicado, com reenvio automático com um clique para quem não visualizou.
* **Autorizações Digitais em 1 Toque:** Autorizações formais de saídas a campo, passeios pedagógicos, uso de imagem e administração de remédios com validade jurídica e registro de data/hora.
* **Enquetes e Votações:** Pesquisas de satisfação (NPS escolar), consultas para escolha de temas de eventos, enquetes de interesse de matérias eletivas.
* **Notificações Ativas via WhatsApp Oficial (Meta Cloud API):** Disparo de lembretes automáticos e críticos diretamente no WhatsApp da família (ex: "Seu filho acabou de entrar na escola", aviso de falta inesperada, boleto do mês).
* **Agendamento de Reuniões Pedagógicas (Plantão de Pais):** Módulo tipo Calendly/Google Calendar no qual a escola disponibiliza janelas de 15 minutos dos professores e os pais reservam seu horário online.

---

### Módulo 2: Gestão Acadêmica, Diário de Classe e Avaliações

O coração pedagógico da escola, focado em reduzir a carga de trabalho burocrático dos professores e dar visibilidade aos pais.

* **Diário de Classe Web e Mobile (Offline-First / PWA):** Lançamento de frequência e plano de aula mesmo em locais da escola sem internet, sincronizando assim que reconectar.
* **Chamada Inteligente Integrada:** Chamada pré-preenchida automaticamente a partir dos dados da catraca ou reconhecimento facial da portaria, cabendo ao docente apenas confirmar exceções.
* **Alinhamento à BNCC e Currículo:** Vinculação de conteúdos, habilidades e competências da Base Nacional Comum Curricular (BNCC) no planejamento de cada aula.
* **Avaliações Flexíveis e Médias Customizáveis:** Suporte a notas numéricas (0-10, 0-100), conceitos (A-F, Insuficiente a Excelente), pesos por atividade, arredondamento automático, recuperação paralela e final.
* **Banco de Questões e Correção por Gabarito OCR:** Montagem de provas com questões de vestibular/ENEM/autorais e correção automática através da câmera do celular escaneando a folha de respostas.
* **Fechamento e Emissão de Boletim Digital:** Geração instantânea de boletim em PDF com gráficos de comparação com a média da turma e histórico escolar.
* **Pareceres Descritivos Assistidos por IA:** Co-geração de rascunhos de relatórios de desenvolvimento para Educação Infantil e Ensino Fundamental I baseados nos registros e ocorrências do bimestre, com revisão obrigatória do professor.
* **Alerta Precoce de Evasão e Desempenho (Early Warning System):** Algoritmo que detecta quedas bruscas de rendimento, acúmulo de faltas consecutivas e inadimplência, disparando sinal amarelo para a coordenação pedagógica.

---

### Módulo 3: Inclusão, Neurodiversidade e Saúde (PEI & Bem-Estar)

Uma das maiores dores das escolas atuais diante do aumento de diagnósticos de TEA (Autismo), TDAH, dislexia e deficiências.

* **Módulo PEI (Plano Educacional Individualizado):** Plataforma para elaboração colaborativa do PEI entre professor regente, professor de AEE (Atendimento Educacional Especializado) e terapeutas externos.
* **Definição e Acompanhamento de Metas SMART:** Registro de objetivos educacionais por ciclo (trimestral/semestral) com barra de evolução e evidências anexadas.
* **Histórico e Repositório de Laudos Médicos Sigilosos:** Gestão de documentos de saúde com proteção especial da LGPD (dados sensíveis com controle restrito de quem tem permissão para visualizar).
* **Ficha Médica e Enfermaria Escolar:** Cadastro de alergias alimentares/medicamentosas, tipo sanguíneo, contatos de emergência e registro de atendimentos realizados na enfermaria escolar.
* **Controle de Medicamentos com Receita:** Fluxo de autorização em que o responsável anexa a receita médica e agenda os horários em que a escola deve medicar a criança.

---

### Módulo 4: Segurança Física, Portaria e Logística de Saída

Foco em segurança de ponta, redução do trânsito na porta da escola e tranquilidade para os responsáveis.

* **Reconhecimento Facial e Catraca Inteligente:** Validação biométrica no portão da escola com registro instantâneo de horário de entrada e saída.
* **Push Notification Imediato na Entrada e Saída:** O responsável recebe no celular a confirmação do horário exato em que o estudante passou pela catraca.
* **Gestão de Saída e Fila de Veículos (Estilo "Filho sem Fila"):** O app dos pais detecta quando eles estão a 500 metros da escola (via geolocalização / GPS) ou por toque de check-in, chamando o aluno no telão da sala/pátio para que ele esteja na calçada quando o carro encostar.
* **Autorização de Terceiros e Saídas Avulsas:** Liberação no app para que tios, avós ou motoristas de aplicativo retirem o aluno, gerando QR Code de segurança temporário com validade e upload de documento.
* **Carteirinha Digital do Estudante:** Carteirinha no app com QR code dinâmico anti-cópia para acesso, empréstimo de livros e descontos de meia-entrada.
* **Achados e Perdidos Digital:** Catálogo visual de itens esquecidos na escola (agasalhos, garrafas, estojos) com fotos para resgate pelos pais.

---

### Módulo 5: Secretaria Digital, Captação e Matrícula Online

Eliminação completa de papel e burocracia de balcão, permitindo que a escola funcione 24/7.

* **CRM Escolar e Funil de Captação:** Gestão de novos contatos interessados, agendamento de visitas presenciais guiadas e mensagens de acompanhamento.
* **Esteira de Matrícula e Rematrícula 100% Online:**
  * Preenchimento de ficha cadastral pelo responsável em qualquer dispositivo.
  * Upload e leitura automatizada de documentos (RG, certidão de nascimento, comprovante de residência, carteira de vacinação) com validação via OCR.
  * Análise cadastral e antifraude.
  * Geração automática de contrato de prestação de serviços com cláusulas customizadas.
  * Assinatura digital/eletrônica integrada (validade jurídica avançada ou ICP-Brasil).
  * Pagamento da taxa de matrícula / primeira mensalidade integrado via Pix instantâneo.
* **Autoatendimento da Secretaria:** Solicitação de 2ª via de histórico, declaração de matrícula, atestado de frequência com validação de autenticidade por código QR público dispensando carimbo físico.
* **Exportação e Integração com Censo Escolar (Educacenso / INEP):** Geração do arquivo no layout exigido pelo governo federal sem necessidade de redigitação manual de alunos e turmas.

---

### Módulo 6: Gestão Financeira, Cobrança e Serviços Adicionais

Sustentabilidade financeira da escola, redução drástica da inadimplência e novas fontes de receita.

* **Régua de Cobrança Multicanal Automatizada:** Lembretes automáticos antes do vencimento (-5 dias), no dia do vencimento e após o vencimento (+3, +7, +15 dias) via WhatsApp, Push, E-mail e SMS.
* **Pix Dinâmico com Baixa em Tempo Real:** QR Code Pix atrelado a cada mensalidade com compensação financeira e liberação no sistema em poucos segundos.
* **Boleto Híbrido (Boleto com Pix):** O documento impresso ou digital contém tanto o código de barras tradicional quanto o QR Code Pix.
* **Cartão de Crédito Recorrente:** Cobrança mensal automática no cartão sem bloquear o limite global do titular (funciona como assinatura).
* **Portal de Negociação e Acordo de Dívidas:** Espaço onde o inadimplente pode simular parcelamento de débitos atrasados e assinar termo de confissão de dívida online.
* **Cantina Escolar Digital Cashless:**
  * Carteira digital recarregável no app da família.
  * Pagamento na cantina por biometria facial, totem de autoatendimento ou QR Code da carteirinha.
  * Limite diário de gastos e bloqueio de alimentos por alergia alimentar (glúten, lactose, açúcar).
  * Extrato de consumo detalhado para os pais.
* **Gestão de Transporte Escolar (Vans):** Cadastro de itinerários, lista de embarque de passageiros e status de trajeto.
* **Loja Escolar e Cobrança de Eventos:** Compra de uniformes, material paradidático, taxas de passeios e formaturas pelo app.
* **Biblioteca Escolar:** Busca no acervo, controle de empréstimos, notificações de devolução e reservas de livros.

---

### Módulo 7: Inteligência Artificial (IA) e Automação Operacional

A fronteira tecnológica mais recente adotada pelas principais EdTechs.

* **Agente de Atendimento Virtual (Chatbot Escolar com RAG):** IA alimentada com o regimento escolar, calendário de provas e manuais da escola para responder dúvidas recorrentes de pais e alunos 24 horas por dia.
* **Copiloto Pedagógico para Professores:** Geração de sugestões de atividades diferenciadas para alunos com dificuldades específicas e criação de rubricas de avaliação.
* **Gerador Inteligente de Grade de Horários (Timetable Solver):** Otimizador matemático que monta os horários semanais das turmas respeitando disponibilidade dos professores, limitações de salas/laboratórios e proibição de janelas vagas indesejadas.
* **Transcrição e Resumo de Reuniões Pedagógicas:** Gravação e síntese automática de reuniões de conselho de classe e reuniões de pais.

---

### Módulo 8: Governança, Multiunidades e Compliance Legal

* **Multiunidades e Franquias (Multi-Tenant Real):** Gestão centralizada para redes com múltiplas filiais, permitindo visualização consolidada de indicadores (BI) e isolamento seguro entre unidades.
* **Conformidade Estrita com LGPD e ECA Digital:** Ferramentas de opt-in/opt-out para dados de menores, termo de aceite de privacidade e registros imutáveis de auditoria transacional.

---

## 3. Matriz de Benchmarking e Cruzamento com o SIESCO

Avaliando o estado atual do **SIESCO Portal Escolar** (conforme documentado na v1 e no roadmap/tracking do projeto):

| Módulo / Funcionalidade | Status no SIESCO Atual | Tendência de Mercado | Nível de Viabilidade no SIESCO | Impacto no Produto | Recomendação Estratégica |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Autenticação, Sessões e Perfis Básicos** | ✅ Implementado | Padrão Mandatório | N/A (Já feito) | Alto | Manter padrão de sessão opaca e RLS |
| **Cadastro Institucional e Turmas/Disciplinas** | ✅ Implementado | Padrão Mandatório | N/A (Já feito) | Alto | Base sólida construída |
| **Vínculos Familiares e Matrículas Básicas** | ✅ Implementado | Padrão Mandatório | N/A (Já feito) | Alto | Base sólida construída |
| **Calendário, Ano Letivo e Períodos** | 🟡 No Tracking (ACA-01) | Padrão Mandatório | **Alta** (Imediata) | Essencial | Prioridade 1 do ciclo acadêmico |
| **Diário de Aulas e Frequência** | 🟡 No Tracking (ACA-02) | Padrão Mandatório | **Alta** (Imediata) | Essencial | Prioridade 1 do ciclo acadêmico |
| **Avaliações, Notas e Médias** | 🟡 No Tracking (ACA-03) | Padrão Mandatório | **Alta** (Imediata) | Essencial | Prioridade 1 do ciclo acadêmico |
| **Boletim Digital do Aluno** | 🟡 No Tracking (ACA-04) | Padrão Mandatório | **Alta** (Imediata) | Essencial | Prioridade 1 do ciclo acadêmico |
| **Transferência e Troca de Turma** | 🟡 No Tracking (MAT-01) | Padrão Mandatório | **Alta** (Imediata) | Alto | Completar esteira de secretaria |
| **Comunicação: Mural de Avisos com Confirmação** | 🟡 No Tracking (EXP-01) | Muito Forte | **Alta** (Fácil com Next+FastAPI) | Altíssimo | Antecipar do backlog EXP-01 |
| **Notificações via WhatsApp (Meta Cloud API)** | ⚪ Não planejado | Diferencial Crítico no Brasil | **Média** (Integração externa) | Altíssimo | Transformador para adesão dos pais |
| **Autorizações Digitais em 1 Toque** | ⚪ Não planejado | Muito Forte | **Alta** (Model simples de aceite) | Muito Alto | Alto valor percebido pelas famílias |
| **Módulo Inclusão / PEI (TEA, TDAH, AEE)** | ⚪ Não planejado | Alta Procura / Poucos têm | **Média** (Modelagem pedagógica) | Diferencial Raro | Grande diferencial competitivo |
| **Ficha Médica e Enfermaria Escolar** | ⚪ Não planejado | Crescente | **Alta** (Tabelas de saúde + permissão) | Alto | Segurança e fidelização |
| **Matrícula Online com Assinatura Digital** | ⚪ Não planejado | Tendência Forte | **Média** (Integração ZapSign/Clicksign) | Muito Alto | Economiza semanas de trabalho da secretaria |
| **Régua de Cobrança e Pix Automático** | ⚪ Fora do MVP atual | Tendência Forte | **Média/Baixa** (Gateways como Asaas/Iugu)| Muito Alto | Módulo futuro pós-acadêmico |
| **IA Copiloto para Parecer Descritivo** | ⚪ Não planejado | Novidade 2025/2026 | **Alta** (API Gemini/OpenAI na API) | Alto | Encanta os professores |
| **Saída Inteligente ("Filho sem Fila")** | ⚪ Não planejado | Novidade Forte em SP/Grandes Cidades | **Média** (WebSockets / Push) | Médio/Alto | Útil para escolas particulares urbanas |
| **Catraca / Reconhecimento Facial Integrado** | ⚪ Não planejado | Hardware dependente | **Baixa** (Exige integradores físicos) | Médio | Deixar apenas API aberta/webhooks |
| **Cantina Digital Cashless** | ⚪ Fora do MVP atual | Específico | **Baixa** (Novo domínio de negócio) | Médio | Manter fora do escopo inicial |

---

## 4. Oportunidades de Ouro (Quick Wins & Grandes Diferenciais para o SIESCO)

Ao analisar a arquitetura técnica do SIESCO (FastAPI + PostgreSQL com RLS + Next.js com shadcn/ui), destacam-se oportunidades que trazem **altíssimo valor comercial e facilidade de implementação**:

### 1. Comunicação Direta com "Confirmação de Leitura" e "Autorizações em 1 Toque"
* **Por que adotar:** Escolas sofrem com papéis de passeios perdidos na mochila e recados que pais alegam não ter visto.
* **Complexidade no SIESCO:** Baixa. Criação de tabelas `notices`, `notice_reads`, `authorizations` e `authorization_responses` isoladas por `institution_id` no RLS.

### 2. Disparo de Avisos Críticos e Faltas via WhatsApp Oficial
* **Por que adotar:** No Brasil, os pais muitas vezes demoram para abrir o portal web, mas lêem mensagens de WhatsApp em menos de 3 minutos.
* **Complexidade no SIESCO:** Média. Integração via webhook/API oficial (ex: Evolution API ou Meta WhatsApp Cloud API) para disparo de templates homologados (ausência do dia, boletim disponível).

### 3. Módulo PEI (Plano Educacional Individualizado) para Alunos com TEA/TDAH
* **Por que adotar:** Escolas particulares e públicas são obrigadas por lei a ter planos de adaptação curricular para alunos com neurodivergência ou deficiência. Quase nenhum sistema concorrente tem isso nativo e bem feito.
* **Complexidade no SIESCO:** Média. Registro de metas, adaptações e pareceres com controle de sigilo restrito (RLS refinado para equipe multidisciplinar e responsáveis).

### 4. Assistente de IA para Rascunho de Pareceres Descritivos e Planos de Aula
* **Por que adotar:** Professores passam semanas digitando pareceres descritivos individuais no final do semestre. Um botão "Sugerir rascunho de parecer com base nas ocorrências e notas" economiza centenas de horas de trabalho docente.
* **Complexidade no SIESCO:** Baixa/Média. Uma rota de backend no FastAPI chamando LLM com prompt estruturado e dados anônimos (sem vazar PII).

### 5. Secretaria Digital com Verificação Pública por QR Code
* **Por que adotar:** Emissão de declarações de matrícula em PDF com link e código hash verificável publicamente em `/verificar-documento/{hash}` sem precisar de login. Elimina filas na secretaria e carimbos físicos.
* **Complexidade no SIESCO:** Baixa. Rota pública no Next.js consultando o hash da declaração no backend.

---

## 6. Roteiro Recomendado de Evolução em Ondas para o SIESCO

Para manter o foco e não dispersar os esforços antes da validação do piloto:

1. **Onda 1: Consolidação do Ciclo Acadêmico (Já no Tracking do SIESCO)**
   * Calendário escolar e períodos letivos.
   * Diário de classe, conteúdos ministrados e frequência.
   * Lançamento de avaliações, cálculo de médias e recuperação.
   * Emissão e publicação de boletins escolares para pais e alunos.

2. **Onda 2: Experiência da Família & Secretaria Ágil (Diferencial Prático Imediato)**
   * Mural de avisos e comunicados com confirmação de leitura.
   * Autorizações digitais em 1 toque (passeios, termos de imagem).
   * Emissão de declarações e históricos em PDF com validação pública por QR Code.

3. **Onda 3: Comunicação Ativa & Inclusão (Grande Vantagem Competitiva no Mercado)**
   * Notificações ativas via WhatsApp (faltas diárias, avisos urgentes, boletins).
   * Módulo PEI (Plano Educacional Individualizado) para neurodiversidade e inclusão (TEA/TDAH).
   * Ficha médica e enfermaria escolar com alertas de alergias.

4. **Onda 4: Ecossistema Avançado & IA (Escala Comercial)**
   * Matrícula e rematrícula online com upload de docs e assinatura eletrônica.
   * Copiloto de IA para auxílio na redação de pareceres descritivos.
   * Módulo financeiro integrado com emissão de Pix dinâmico e régua de cobrança automática.
