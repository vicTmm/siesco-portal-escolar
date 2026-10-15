# Acompanhamento do SIESCO

Atualizado em 15/10/2026. Fonte contínua de acompanhamento: atualizar este arquivo a cada entrega, com status, evidência de validação e próximo passo. O roadmap descreve a sequência; este arquivo registra o andamento real. Concluir implementação não equivale a homologar produção.

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
| BASE-01 | Base | Login, perfis, instituições, pessoas, disciplinas, turmas, vínculos, matrículas e dashboard | Validado | Suítes de API e os seis fluxos originais de navegador aprovados com API real; homologação institucional continua antes do piloto. |
| SITE-01 | Atual | Landing page sobre o SIESCO com destaque para acesso online | Validado | Rota pública /sobre, sem dependência da API; build e layout em quatro larguras aprovados. Publicação externa fica em OPS-01. |
| SITE-02 | Atual | Navegação app → site → app | Validado | Fluxos site/login/site e menu/site verificados em navegador no build de produção, com sessões simuladas. |
| QA-01 | Alta | Executar os seis cenários E2E existentes e revisar visualmente o app | Validado | Seis fluxos originais aprovados com API/PostgreSQL reais; revisão visual desktop/móvel. Novo fluxo acadêmico também aprovado. |
| QA-02 | Alta | Validar build e execução do Docker Compose e CI no GitHub | Em andamento | CI anterior aprovada (run 38460130839); Docker local sem daemon, execução completa de containers permanece pendente. |
| ACA-01 | Alta | Calendário, ano letivo, períodos/bimestres e currículo | Validado | Migração 0002, quatro cadastros, currículos publicados imutáveis e vínculo com turma. Ver organizacao-academica.md; datas importadas exigem revisão pela escola. |
| ACA-02 | Alta | Diário de aulas e frequência | Validado | Aulas, chamada em lote, elegibilidade por data, cancelamento, versão concorrente e permissões docentes; testes PostgreSQL e navegador. |
| ACA-03 | Alta | Avaliações, notas, médias e recuperação | Implementado | Modelos simples, ponderado, pontos e conceitos; escala, aprovação, frequência, recuperação e pesos anuais escolhidos pela escola. Fórmulas testadas; homologação institucional pendente. |
| ACA-04 | Alta | Fechamento, reabertura, publicação e boletim | Implementado | Fechamento com pendências bloqueadas, reabertura motivada pela direção, snapshots por período e anuais, consulta familiar e impressão. Fluxo de período validado em produção local. |
| MAT-01 | Alta | Transferência, troca de turma e reativação | Implementado | Intervalos sem sobreposição, motivo obrigatório, capacidade e ano validados. Testes PostgreSQL; conciliação retroativa e equivalências externas precisam de homologação. |
| IAM-01 | Alta | Recuperação/troca de senha, convites e e-mail | Implementado | Tokens de uso único, revogação de sessões, SMTP e caixa local de desenvolvimento; conta existente pode receber vínculo sem redefinir credenciais. SMTP real ainda depende de provedor. |
| IAM-02 | Antes do piloto | MFA e escolha de provedor OIDC | Em andamento | TOTP cifrado, antirrepetição e códigos de recuperação implementados/testados; produção exige MFA da equipe. Provedor OIDC/SSO ainda não escolhido/integrado. |
| OPS-01 | Antes do piloto | Hospedagem, domínio e HTTPS para acesso online 24/7 | Em andamento | Compose de produção e gateway HTTPS preparados. Hospedagem, DNS e ativação externa pendentes; ambiente disponível continua local. |
| OPS-02 | Antes do piloto | Monitoramento, alertas, backups, restauração e incidentes | Em andamento | Scripts de dump, restauração em banco separado e healthcheck; ensaio local aprovado. Agendamento, cópia externa, alertas, metas RPO/RTO e carga dependem da operação escolhida. |
| SEC-01 | Antes do piloto | Revisão de segurança e proteção de dados | Em andamento | CSP com nonce, MFA, controles SQL, tokens e exports protegidos. Revisão independente, retenção/base legal e procedimentos institucionais continuam pendentes. |
| UX-01 | Média | Busca global, filtros e paginação do portal | Implementado | Busca global e por nome nos cadastros; portal familiar com busca/paginação. Busca local permanece em cadastros de relações sem nome próprio. |
| AUD-01 | Média | Consulta de auditoria e motivo de cancelamento | Implementado | Consulta paginada para direção; motivos de movimentação/reabertura preservados; exportações auditadas. |
| ORG-01 | Conforme piloto | Múltiplas unidades e perfis por conta/instituição | Pendente | Hoje uma escola e um perfil por conta/instituição. |
| EXP-01 | Posterior | Avisos, documentos e relatórios | Em andamento | Mock WhatsApp; CSV autorizado e impressão de boletim. Meta real adiada pelo usuário; documentos oficiais assinados/anexos privados continuam expansão específica. |

Financeiro, pagamentos, biblioteca, transporte, LMS e aplicativos nativos continuam fora do MVP; não são bloqueadores do escopo atual.

## Registro das entregas

### 13/10/2026 — Organização acadêmica (ACA-01) e validação da base

- Executados os seis E2E originais com login real, API e PostgreSQL: aprovados. Revisadas capturas desktop/móvel.
- Confirmada CI do commit anterior aprovada no GitHub: run 38460130839. Docker Desktop sem daemon; QA-02 segue aberto para containers.
- Implementados anos letivos, períodos, currículos versionados e matriz de disciplinas/cargas horárias, com telas e APIs.
- Direção e coordenação podem alterar organização acadêmica; secretaria consulta. Professor, aluno e responsável não acessam esses cadastros administrativos.
- Datas dos períodos devem estar dentro do ano letivo, sem sobreposição e na ordem da sequência. Operações concorrentes são serializadas por calendário.
- Currículo exige ao menos uma disciplina para publicação; versão publicada e componentes ficam protegidos na API e no banco. Mudanças exigem uma nova versão.
- Turmas exigem calendário cadastrado; podem vincular currículo publicado da mesma etapa. O vínculo não pode ser substituído e atribuições docentes respeitam a matriz.
- Migração 0002 mantém registros existentes e cria calendários provisórios sinalizados para revisão. Currículo permanece opcional na transição.
- Backend: 44 testes aprovados no PostgreSQL real, incluindo permissões, isolamento, concorrência, auditoria e proteções SQL.
- Frontend/BFF: 13 testes aprovados, incluindo integração com API real. Build e TypeScript aprovados.
- Novo cenário E2E aprovado: cadastro de calendário e períodos, rejeição de sobreposição, matriz, publicação e vínculo à turma; capturas desktop/móvel.
- Downgrade/upgrade de 0002 testado exclusivamente em portal_test: alunos, turmas e matrículas preservados; alembic check sem divergências.
- Próxima entrega: ACA-02, diário de aulas e frequência. Regras de médias, recuperação e aprovação continuam para homologação antes de ACA-03.

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
- [Pesquisa de mercado e benchmarking de funcionalidades](pesquisa-features.md)

Próxima sequência: diário/frequência → avaliações/notas → boletim, com preparação operacional antes do piloto real. Base e organização acadêmica já passaram nas verificações técnicas acima.


### 15/10/2026 — Ciclo acadêmico, acesso e preparação operacional

- Usuário autorizou implementar as pendências. Pediu regras de avaliação selecionáveis pela escola e adiou a integração real da Meta; lembrar após as demais entregas.
- Migrações 0003–0005: diário, chamada, avaliações/notas, regras, publicações imutáveis, movimentação com intervalos, recuperação, MFA e consolidação anual. Referências e RLS mantêm isolamento; guardas SQL reforçam datas, elegibilidade e limites de nota.
- Diário e boletim por período validados com login/API/banco reais no build de produção, inclusive consulta por responsável e layout móvel; testes anteriores continuam passando.
- Backend ampliado com testes de publicação/reabertura/revogação, lote atômico, concorrência, fórmulas, intervalos, reset/MFA e export/auditoria. Evidências finais e ativação externa em diario-avaliacoes.md e operacao-producao.md.
- Dump e restauração ensaiados em banco dedicado portal_restore, sem alterar o banco de uso do portal.
- Produção preparada com Compose/Caddy, MFA obrigatório para equipe, bootstrap sem seed, SMTP configurável e scripts de operação. Não foi feito deploy externo nem ativado monitoramento/SMTP real.
- Limites explícitos: períodos/escala precisam de homologação; abono de frequência, equivalências externas, conselho de classe e documentos oficiais não são inferidos. Múltiplas unidades/perfis continuam ORG-01, conforme piloto.

- Validação local final desta etapa: 56 testes backend, 14 frontend/BFF (incluindo API real), 9 E2E em build de produção; TypeScript/build e alembic check aprovados. Validação Docker/CI será registrada após execução no GitHub.
