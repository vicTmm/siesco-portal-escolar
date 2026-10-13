# Acompanhamento do SIESCO

Atualizado em 13/10/2026. Fonte contínua de acompanhamento: atualizar este arquivo a cada entrega, com status, evidência de validação e próximo passo. O roadmap descreve a sequência; este arquivo registra o andamento real. Concluir implementação não equivale a homologar produção.

Status: **Pendente**, **Em andamento**, **Implementado**, **Validado**. Registrar bloqueios na coluna de observações sem marcar a entrega como concluída.

## Requisito das escolas: acesso online

**Todos os dados acessíveis de qualquer lugar, em qualquer dispositivo, 24 horas por dia, 7 dias por semana.** Requisito reforçado pelo usuário em 13/10/2026.

- Acesso pelo navegador em computador, tablet e celular com internet.
- Dados disponíveis conforme instituição, perfil e vínculos autorizados; acesso online não significa acesso público aos dados escolares.
- Operação online contínua, independente de um computador ligado na escola.
- Aceitação: ambiente hospedado com domínio e HTTPS; fluxos críticos validados em desktop, tablet e celular e por rede externa; monitoramento de disponibilidade e alertas; backups e restauração ensaiados; procedimento de incidentes e manutenção definido.
- Definir meta mensurável de disponibilidade e recuperação com a escola piloto. A mensagem 24/7 expressa o requisito do produto; a demonstração local não comprova disponibilidade de produção.

## Entregas e pendências

| ID | Prioridade | Entrega | Status | Observações / próximo passo |
| --- | --- | --- | --- | --- |
| BASE-01 | Base | Login, perfis, instituições, pessoas, disciplinas, turmas, vínculos, matrículas e dashboard | Implementado | Validações anteriores registradas em implementacao-v1.md; falta homologação completa no navegador. |
| SITE-01 | Atual | Landing page sobre o SIESCO com destaque para acesso online | Validado | Rota pública /sobre, sem dependência da API; build e layout em quatro larguras aprovados. Publicação externa fica em OPS-01. |
| SITE-02 | Atual | Navegação app → site → app | Validado | Fluxos site/login/site e menu/site verificados em navegador no build de produção, com sessões simuladas. |
| QA-01 | Alta | Executar os seis cenários E2E existentes e revisar visualmente o app | Pendente | Cobrir desktop, móvel, permissões e fluxos integrados. Não confundir inspeção da landing com homologação do app. |
| QA-02 | Alta | Validar build e execução do Docker Compose e CI no GitHub | Pendente | Configuração foi validada anteriormente; execução completa ainda não comprovada. |
| ACA-01 | Alta | Calendário, ano letivo, períodos/bimestres e currículo | Pendente | Homologar regras da escola antes de implementar cálculos. |
| ACA-02 | Alta | Diário de aulas e frequência | Pendente | Aulas, conteúdo, chamada, pendências e permissões docentes. |
| ACA-03 | Alta | Avaliações, notas, médias e recuperação | Pendente | Definir escala, pesos, arredondamento e aprovação. |
| ACA-04 | Alta | Fechamento, reabertura, publicação e boletim | Pendente | Famílias acessam somente resultados publicados; preservar versões e histórico. |
| MAT-01 | Alta | Transferência, troca de turma e reativação | Pendente | Preservar histórico e períodos de alocação; resolver matrícula cancelada no mesmo ano. |
| IAM-01 | Alta | Recuperação/troca de senha, convites e e-mail | Pendente | Incluir primeiro acesso e vínculo de conta já existente. |
| IAM-02 | Antes do piloto | MFA e escolha de provedor OIDC | Pendente | Homologar acesso de equipe e recuperação de contas. |
| OPS-01 | Antes do piloto | Hospedagem, domínio e HTTPS para acesso online 24/7 | Pendente | Requisito das escolas acima; demonstração continua local. |
| OPS-02 | Antes do piloto | Monitoramento, alertas, backups, restauração e incidentes | Pendente | Ensaiar recuperação e medir disponibilidade; testar carga. |
| SEC-01 | Antes do piloto | Revisão de segurança e proteção de dados | Pendente | CSP, segredos, proteção contra abuso, retenção e procedimentos institucionais. |
| UX-01 | Média | Busca global, filtros e paginação do portal | Pendente | Busca atual só na página; portal limitado a 100 alunos. |
| AUD-01 | Média | Consulta de auditoria e motivo de cancelamento | Pendente | Ampliar eventos e revisão operacional. |
| ORG-01 | Conforme piloto | Múltiplas unidades e perfis por conta/instituição | Pendente | Hoje uma escola e um perfil por conta/instituição. |
| EXP-01 | Posterior | Avisos, documentos e relatórios | Pendente | Expansões separadas após ciclo acadêmico. |

Financeiro, pagamentos, biblioteca, transporte, LMS e aplicativos nativos continuam fora do MVP; não são bloqueadores do escopo atual.

## Registro das entregas

### 13/10/2026 — Tracking e apresentação do produto

- Salva a avaliação de pendências e a ordem de prioridade.
- Registrado o requisito de acesso online das escolas e seus critérios de aceitação.
- Criada landing page em /sobre, com recursos existentes, públicos atendidos e proposta de acesso 24/7.
- Adicionados links no login e no menu autenticado para o site, e links do site para o app.
- Build de produção Next.js aprovado, incluindo verificação TypeScript e geração estática de /sobre.
- Vitest: 12 testes aprovados; 1 teste de integração com API real não executado (INTEGRATION_API desabilitada).
- Landing respondeu HTTP 200. Layout conferido em navegador Chrome nas larguras 1440, 768, 390 e 320 px, sem rolagem horizontal; capturas em apps/web/test-results/siesco-site-*.png, com inspeção visual desktop/móvel.
- Navegação site → login → site e menu autenticado → site aprovada no build de produção. Sessões simuladas para isolar navegação; não representa validação de autenticação real nem execução dos seis E2E existentes.
- Sem erros JavaScript nos fluxos de navegador verificados. Publicação externa, disponibilidade 24/7 e homologação completa do app continuam pendentes.

## Referências

- [Implementação e verificações anteriores](implementacao-v1.md)
- [Roadmap e critérios por etapa](roadmap.md)
- [Módulos e permissões](modulos.md)

Próxima sequência: validar a base atual → organização acadêmica → diário/frequência → avaliações/notas → boletim, com preparação operacional antes do piloto real.
