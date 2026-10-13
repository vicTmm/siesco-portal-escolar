# Arquitetura recomendada

Status: arquitetura de referência. A implementação parcial e suas simplificações estão em [implementacao-v1.md](implementacao-v1.md). Premissa inicial: educação básica, uma instituição pode administrar várias escolas; cursos e regras acadêmicas devem ser validados com a escola piloto. Recursos aqui descritos são requisitos próprios, não funcionalidades comprovadas da referência.

## Decisões principais

Adotar monólito modular FastAPI e banco compartilhado com isolamento por instituição. Essa opção simplifica transações de matrícula e fechamento acadêmico e reduz o custo operacional inicial. Evitar microserviços antes de existir necessidade de escala ou equipes independentes. Um banco por instituição oferece isolamento operacional maior, mas aumenta migrações e manutenção; reconsiderar para contratos que o exijam.

| Camada | Escolha e responsabilidade |
| --- | --- |
| Interface | Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui; páginas e componentes próprios, acessíveis por teclado |
| BFF | Route Handlers do Next.js: sessão web, proteção CSRF e encaminhamento autenticado; sem regras acadêmicas ou acesso direto ao banco |
| Domínio/API | FastAPI, Pydantic, SQLAlchemy e Alembic; autorização, validação, transações e OpenAPI |
| Persistência | PostgreSQL; constraints, índices, histórico e RLS para instituição |
| Processamento posterior | Worker do mesmo código de domínio, jobs persistidos e outbox no PostgreSQL; fila dedicada somente se necessária |
| Arquivos futuros | Armazenamento de objetos privado, metadados no banco, acesso temporário autorizado |
| Desenvolvimento | Docker Compose: web, api, db; worker e servidor de e-mail de teste quando usados |

Fluxo: navegador → Next.js/BFF → FastAPI → PostgreSQL. O BFF mantém credenciais de backend fora do JavaScript do navegador; o backend valida novamente usuário, instituição, escola e objeto. O navegador nunca fala diretamente com o banco. Jobs carregam contexto autorizado explícito e revalidam o vínculo ao executar.

## Instituição e escola

`institution` é o tenant contratual. `school` é uma unidade desse tenant. Todo registro de negócio possui `institution_id`; registros escolares também possuem `school_id`. Membros recebem perfis por escola. A direção de uma unidade não ganha acesso às outras automaticamente. Operações institucionais exigem concessão explícita separada. Uma pessoa que participa de duas instituições mantém cadastros pessoais separados em cada uma; a identidade de login pode ser global.

A API valida o tenant da URL contra a sessão e os vínculos ativos. Não confia em um header ou campo do cliente como autorização. Usar transação por requisição, contexto com `SET LOCAL` e RLS com `USING`/`WITH CHECK`. Ausência de contexto deve negar acesso. Papel da aplicação não é proprietário, superusuário nem `BYPASSRLS`; aplicar `FORCE ROW LEVEL SECURITY`. Papel de migração separado. RLS é defesa para tenant; escopo de escola e vínculo acadêmico também são verificados no serviço.

O administrador da plataforma gerencia instituições e disponibilidade, sem leitura acadêmica por padrão. Suporte excepcional exige concessão temporária, motivo, aprovação institucional e auditoria; nunca um bypass silencioso.

## Sessões e cache

Recomenda-se autenticação OIDC com provedor mantido, Authorization Code + PKCE, MFA para equipes privilegiadas e sessões opacas no BFF. Cookie HttpOnly, Secure em produção e SameSite; tokens armazenados apenas no servidor e nunca em localStorage. FastAPI valida assinatura, emissor, audiência e expiração dos tokens. Perfis e vínculos são consultados no banco, com revogação efetiva; não confiar apenas em claims antigos.

Páginas com dados pessoais e boletins usam `no-store`, sem cache público. Se cache privado for introduzido, chave inclui tenant, escola, usuário e versão de permissão; invalidação acompanha revogação. URLs de arquivos, exportações e jobs obedecem ao mesmo escopo.

## API

Prefixo `/api/v1`. Exemplos no backend:

| Rota | Uso |
| --- | --- |
| `GET /me`, `GET /me/memberships` | Identidade e contextos disponíveis |
| `/platform/institutions` | Administração da plataforma |
| `/institutions/{institution_id}/schools` | Unidades autorizadas |
| `/institutions/{institution_id}/schools/{school_id}/academic-years` | Calendário |
| `.../students`, `.../guardians`, `.../classes`, `.../subjects` | Cadastros |
| `.../enrollments`, `.../enrollments/{id}/placements` | Matrícula e movimentação de turma |
| `.../class-subjects/{id}/lessons` | Diário |
| `.../lessons/{id}/attendance` | PUT em lote, atômico |
| `.../class-subjects/{id}/assessments`, `.../assessments/{id}/grades` | Avaliações e notas |
| `.../terms/{id}/close`, `.../terms/{id}/reopen` | POST com motivo e autorização |
| `.../enrollments/{id}/report-card` | Somente dados publicados |
| `.../audit-events` | Consulta restrita e paginada |

Listagens têm paginação limitada, filtros permitidos e ordenação estável. Erros contêm código, mensagem segura e request_id: 401 sem sessão, 403 ação proibida, 404 objeto inexistente ou fora do escopo, 409 conflito/versão, 422 validação. OpenAPI é fonte do cliente TypeScript gerado; DTOs ocultam campos por perfil. Não devolver entidades ORM completas.

Usar versão otimista/ETag em lançamentos e correções, retornando 409/412 para edição concorrente. Criação de matrícula e comandos de fechamento aceitam idempotency key scoped por tenant/ator/operação, com hash do payload. Alteração acadêmica e evento de auditoria pertencem à mesma transação; falha de auditoria aborta a mutação. Notificações saem de outbox após commit.

## Organização prevista do repositório

```text
apps/web/src/{app,components,features,lib}
apps/api/app/{core,db,modules}
apps/api/app/modules/{identity,tenancy,people,academic,enrollment,diary,assessment,portal,audit}
apps/api/migrations/
apps/api/tests/{unit,integration,authorization}
packages/api-client/
infra/{compose.yaml,docker,env.example}
tests/e2e/
docs/
```

Cada módulo backend separa router, schemas, service, repository e models. Serviços chamam serviços de outros módulos por contratos explícitos. Banco é acessado somente nos repositories dentro da transação do caso de uso. Constraints continuam responsáveis por integridade sob concorrência.

## Operação e validação

Compose deve iniciar com um comando documentado, healthchecks e migrações controladas; dados de seed sintéticos para duas instituições. Segredos não entram no Git. Versões suportadas devem ser fixadas em lockfiles na primeira entrega, após verificar compatibilidade, sem usar tags `latest`.

Produção exige TLS, backups criptografados, PITR, restauração ensaiada, monitoramento de falhas e migrações compatíveis com rollback da aplicação. Metas propostas para o piloto: RPO ≤ 15 minutos, RTO ≤ 4 horas; confirmar orçamento antes de tratar como compromisso. Medir p95 ≤ 500 ms para consultas comuns, com 50 usuários simultâneos e dataset sintético documentado, excluindo exports e rede externa.

Testes essenciais: cruzamento de tenant/escola/objeto em todas as rotas, conta com múltiplos vínculos, revogação de responsável, reuso de conexão, concorrência de matrícula/notas, publicação e reabertura. Dados reais não são usados em ambientes de desenvolvimento.

## Fontes técnicas

- [Next.js Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers): mecanismo recomendado para o BFF.
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/): integração de mecanismos de segurança na API.
- [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html): políticas por linha, negação padrão e exceções de owner/superuser/BYPASSRLS.
