# Implementação v0.1

Data: 13/10/2026. Este registro complementa a arquitetura proposta e descreve o que foi efetivamente implementado. Os seis documentos iniciais continuam como visão de evolução, não como afirmação de funcionalidades prontas.

## Escopo entregue

| Área | Implementação |
| --- | --- |
| Identidade | Senha Argon2, sessão aleatória com hash no banco, validade de 8 horas, logout e limitação de tentativas por conta |
| Perfis | Plataforma, diretor, coordenador, secretaria, professor, aluno, responsável; autorização em cada operação da API |
| Instituição | Cadastro pela plataforma, escola principal e primeiro diretor na mesma transação |
| Pessoas | Criação/lista/edição de alunos, responsáveis e professores; nascimento validado, e-mails normalizados |
| Organização | Disciplinas, turmas por ano, turno, etapa e capacidade; atribuição de professor e disciplina à turma |
| Matrícula | Cadastro, unicidade por aluno/escola/ano, lock de turma para capacidade, cancelamento preservando histórico |
| Vínculos | Responsável/aluno com verificação explícita e revogação; professor limitado a alunos de turmas atribuídas |
| Gestão de acesso | Diretor cria conta e perfil; vínculo obrigatório para aluno, responsável e professor; revogação imediata da membership |
| Interface | Login, dashboard, tabelas paginadas, formulários com foco/modal acessível, mensagens de erro, carregamento e layout responsivo |
| Persistência | PostgreSQL, Alembic, RLS, FKs compostas, auditoria de mutações, duas instituições fictícias |

## Decisões e limitações explícitas

1. **OIDC/MFA adiados.** A autenticação local permite demonstrar o sistema sem contratar provedor. Não há recuperação de senha, convite por e-mail, MFA ou política de troca inicial. Não há envio de e-mail.
2. **Uma escola por instituição**, garantida por UNIQUE em schools.institution_id. Todos os registros escolares e vínculos guardam school_id; uma futura migração deverá remover a restrição e introduzir concessões por unidade. Há um perfil por conta/instituição; a modelagem de múltiplos perfis fica para evolução.
3. **Ano e etapa simplificados na turma.** Calendários, períodos, currículos e políticas de avaliação ainda não possuem entidades próprias. Não há notas, diário, frequência, financeiro ou boletim.
4. **Matrícula sem transferência/reativação.** Cancelamento mantém registro e unicidade anual; rematrícula do mesmo aluno/ano é rejeitada. Antes de implementar reativação ou movimentação, introduzir eventos e alocações conforme o modelo proposto. Não existe chave de idempotência nesta versão; retries duplicados retornam conflito.
5. **Cadastro de pessoa é separado de conta.** Professor/responsável cadastrado não ganha login automaticamente. O diretor cria a conta escolhendo o registro já existente. Uma conta com e-mail global existente não é vinculada silenciosamente a outra instituição; falta o fluxo de convite/verificação de identidade.
6. **API inicial compacta.** Models, schemas, segurança e persistência estão separados; rotas/casos de uso estão em main.py. Separação completa em módulos e cliente TypeScript gerado ainda não foram feitas.
7. **RLS cobre dados escolares.** Usuários, sessões, tentativas de login, catálogo institucional e memberships são tabelas globais de identidade/control plane, acessíveis somente por rotas autorizadas. RLS não substitui essas verificações. A aplicação não tem owner, superuser ou BYPASSRLS; migração usa credencial separada.
8. **Auditoria inicial.** Mutação e evento compartilham transação, finalizada antes da resposta; runtime não altera/exclui auditoria. Os eventos contêm ator, ação, escola, objeto e instante, sem payload pessoal. Export imutável, trilha de leitura, motivo obrigatório de cancelamento e revisão operacional ainda faltam.
9. **Consultas.** Listagens administrativas paginam em blocos de até 100; interface exibe 50 e busca na página corrente. Selects de referências carregam páginas autorizadas. Portal de vínculos está limitado aos primeiros 100 alunos; paginação específica desse portal ainda deve evoluir para grandes turmas/carteiras.
10. **Cookie e CSRF.** BFF entrega apenas cookie HttpOnly/Secure/SameSite Strict e impede mutações com Origin diferente da origem configurada. Não retorna o token ao JavaScript do browser. O backend usa Bearer. Usar localhost na demonstração, HTTPS em outros ambientes. CSP completa e revisão de exposição de endpoints ainda são necessárias.

## Etapas e verificação

### 1. Banco e backend

Executados no PostgreSQL 18 local, em cluster separado do serviço existente: criação de papel não privilegiado, migração, seed e primeira suíte de 27 testes. Testados autenticação, expiração/logout, bloqueio de tentativas, todos os perfis, isolamento de todas as rotas tenant, CRUD, vínculos, atribuições, validação, auditoria, matrícula e concorrência.

A migração foi congelada em SQL explícito, sem depender do estado futuro dos models. Em `portal_test`, downgrade/reaplicação e os 27 testes passaram. A suíte foi ampliada com permissões adicionais, idempotência do seed e FK contra relação entre instituições; resultados finais registrados abaixo.

### 2. Interface e integração

TypeScript e build Next.js passaram. Suíte Vitest com componentes em DOM de teste e handlers do BFF: carregamento, erro recuperável, ausência de controles para perfil sem escrita, criação/edição, validação, CSRF, sessão ausente/expirada, cookie protegido, falha de rede e caminho inválido. Inclui integração BFF → API real (login, consulta do dashboard, logout e tentativa após revogação), sem servidor frontend.

Os seis testes Playwright estão escritos para desktop/móvel, fluxo completo de cadastros/matrícula, login/logout, família, instituição e CSRF, mas **não foram executados nesta sessão**. A revisão automática rejeitou as duas tentativas de iniciar o servidor Next.js, inclusive mantendo Secure; retornou somente “blocked by policy”. Não houve inspeção visual nem validação em navegador. A CI e o README fornecem execução reproduzível quando o servidor puder iniciar.

### 3. Empacotamento

Compose com serviços db, migrate, seed, api, web e test; dependências por saúde/conclusão e portas em loopback. Configuração verificada com `docker compose --env-file .env.example config --quiet`. **Build/execução de containers não foram validados**, pois o daemon Docker não estava disponível. A API foi executada nativamente e a integração real foi testada nessa modalidade.

## Antes de dados reais

Revisão de segurança, adequação de base legal/retenção e regras da instituição piloto continuam necessárias. Prioridades: OIDC/MFA, recuperação e convites, TLS e CSP, gestão/rotação de segredos, proteção contra abuso distribuído, testes de carga, backups/restauração, suporte a direitos, observabilidade e trilha de auditoria ampliada. Credenciais e dados do seed são somente demonstração.

## Execução

Ver [README](../README.md) para Docker, desenvolvimento nativo, perfis e testes. Não há deploy nem integração com o fornecedor de referência.

## Resultado das verificações

- Backend: **33 testes aprovados** em PostgreSQL 18 real, usando papel de runtime sem bypass. Há um aviso de depreciação da integração Starlette/httpx; não houve falhas.
- Migrações: downgrade/upgrade no banco de teste aprovado; `alembic check` não detectou divergência entre models e banco.
- Frontend/BFF: **13 testes aprovados**, incluindo comunicação com a API real; `tsc --noEmit` e build Next.js aprovados.
- Compose: validação da configuração aprovada; execução de imagens/containers pendente por indisponibilidade do daemon.
- Playwright: seis cenários preparados, não executados por bloqueio da inicialização do servidor frontend. Validação visual pendente.
- CI: workflow adicionado; não executado no GitHub nesta sessão.
