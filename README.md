# Siesco · Portal escolar

O acompanhamento de entregas e pendências está em [docs/tracking.md](docs/tracking.md). Atualize-o a cada avanço. A landing page institucional fica em `/sobre` (localmente, http://localhost:3100/sobre), com links de ida e volta para o app em `/`. O requisito das escolas é acesso online de qualquer lugar e dispositivo, 24 horas por dia, 7 dias por semana; a infraestrutura de produção necessária está acompanhada no tracking.

Primeira versão funcional para demonstração local, com FastAPI, Next.js/TypeScript, Tailwind, componentes no padrão shadcn/ui e PostgreSQL. **Utilize somente dados fictícios. Esta versão não está homologada para produção e exige revisão de segurança.**

## O que está implementado

- Login com Argon2, sessão opaca revogável, logout, limite de tentativas e perfis verificados no servidor.
- Administração da plataforma: cadastro de instituições com criação da escola principal e do primeiro diretor.
- Alunos, responsáveis, professores, disciplinas e turmas: consulta, criação e edição.
- Anos letivos e períodos com validação de datas; currículos versionados, matriz de disciplinas/cargas horárias e publicação protegida. Veja [organização acadêmica](docs/organizacao-academica.md).
- Vínculos familiares verificáveis/revogáveis e atribuição de professor/disciplina à turma.
- Matrículas: criação, prevenção de duplicidade, capacidade sob concorrência e cancelamento com preservação do registro.
- Contas de acesso: criação pelo diretor, perfil e pessoa vinculada; revogação imediata do vínculo.
- Dashboard administrativo responsivo com dados reais da API; portal restrito por vínculo para professor, aluno e responsável.
- Validação no servidor, auditoria transacional, isolamento por instituição com RLS e chaves estrangeiras compostas.
- Migração inicial congelada, seed idempotente de duas instituições fictícias, testes e APIs documentadas.

Uma escola por instituição e um perfil por conta/instituição nesta versão. Os sete perfis são administrador da plataforma, diretor, coordenador, secretaria, professor, aluno e responsável. Consulte as diferenças em relação à arquitetura completa em [docs/implementacao-v1.md](docs/implementacao-v1.md).

## Executar com Docker Compose

Pré-requisitos: Docker com daemon ativo e Compose v2; portas 3100, 8100 e 5433 livres. No Windows, inicie Docker Desktop com containers Linux.

Na raiz do projeto, PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps -a
```

Linux/macOS: use `cp .env.example .env` antes do mesmo comando Compose.

A inicialização espera o banco, aplica migrações, cria a demonstração e sobe API/interface. Os serviços `migrate` e `seed` devem terminar com código 0. Aguarde o build inicial e a API saudável.

| Serviço | Endereço |
| --- | --- |
| Portal | http://localhost:3100 |
| Swagger / teste das APIs | http://localhost:8100/docs |
| ReDoc | http://localhost:8100/redoc |
| Contrato OpenAPI | http://localhost:8100/openapi.json |
| Saúde da API | http://localhost:8100/health |
| PostgreSQL local | localhost:5433, banco `portal`, usuário da aplicação `portal_app` |

Use **localhost** para abrir o portal: o cookie permanece `Secure`, `HttpOnly` e `SameSite=Strict`. Navegadores modernos baseados em Chromium aceitam cookies Secure na exceção local `localhost`; em outros hosts é necessário HTTPS. `APP_ORIGIN` deve corresponder exatamente à origem do navegador. Nenhum token fica no localStorage.

As portas do Compose são publicadas apenas em loopback. As credenciais de `.env.example` são públicas e exclusivas de desenvolvimento. Se alterar senha do PostgreSQL, use caracteres compatíveis com uma URL de conexão ou ajuste sua codificação. Alterar o arquivo não muda a senha de um banco já inicializado.

## Contas de demonstração

Senha inicial de todas as contas: valor de `DEMO_PASSWORD` no `.env`, por padrão `DemoEscolar2026!`.

| Perfil | Conta |
| --- | --- |
| Administrador da plataforma | `admin@demo.example.com` |
| Diretor do Colégio Aurora | `director@aurora.example.com` |
| Coordenador | `coordinator@aurora.example.com` |
| Secretaria | `secretary@aurora.example.com` |
| Professor | `teacher@aurora.example.com` |
| Aluno | `student@aurora.example.com` |
| Responsável | `guardian@aurora.example.com` |
| Diretor da segunda instituição | `director@horizonte.example.com` |

Os outros cinco perfis também existem em `@horizonte.example.com`. Os domínios são reservados para exemplos; nenhum e-mail é enviado. Professor e responsável veem apenas alunos associados aos seus vínculos. A conta da plataforma administra instituições e não consulta os dados acadêmicos delas.

Roteiro: entre como diretor → cadastre aluno e responsável → verifique o vínculo familiar → cadastre professor e disciplina → crie turma e atribuição → faça a matrícula → confira o dashboard. Para testar outro perfil, saia e entre com a respectiva conta.

O seed só executa com `ALLOW_DEMO_SEED=true` e uma `DEMO_PASSWORD` explícita. Rodá-lo novamente preserva os dados e senhas existentes. Não existe reset automático do banco.

## Testes

Backend em PostgreSQL separado (`portal_test`), com migrations e papel de aplicação sem privilégios administrativos:

```powershell
docker compose --profile test run --rm test
```

O comando limpa **somente as tabelas do banco dedicado `portal_test`** antes de cada teste; recusa outro nome de banco ou ausência da habilitação explícita. Não execute testes contra um banco com dados a preservar.

Frontend, com Node.js 24 e npm, na pasta `apps/web`:

```powershell
npm.cmd ci
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

Linux/macOS: use `npm` no lugar de `npm.cmd`. Para incluir a integração BFF → API real, deixe o Compose iniciado e execute:

```powershell
$env:INTEGRATION_API='true'
$env:DEMO_PASSWORD='DemoEscolar2026!'
npm.cmd test
```

Teste de ponta a ponta com o portal em http://localhost:3100 e Google Chrome instalado:

```powershell
$env:DEMO_PASSWORD='DemoEscolar2026!'
npm.cmd run test:e2e
```

Alternativa com navegador de teste: `npx.cmd playwright install chromium` e `$env:PLAYWRIGHT_CHANNEL='chromium'`. Os testes E2E criam registros fictícios com identificadores únicos no banco da demonstração. Capturas ficam em `apps/web/test-results/`. O comando E2E não inicia servidores automaticamente. A integração contínua em `.github/workflows/ci.yml` prepara os serviços e executa as suítes.

Os resultados atuais estão em [docs/tracking.md](docs/tracking.md) e [docs/organizacao-academica.md](docs/organizacao-academica.md). O registro da primeira entrega permanece em [docs/implementacao-v1.md](docs/implementacao-v1.md).

## Desenvolvimento sem Docker

Requer Python 3.14, Node.js 24, PostgreSQL 18 e banco dedicado. Os exemplos abaixo são PowerShell. Na raiz:

```powershell
py -3.14 -m venv .venv
.venv/Scripts/python.exe -m pip install -r apps/api/requirements.txt
```

Em uma instância PostgreSQL de desenvolvimento, execute como administrador, uma vez:

```sql
CREATE ROLE portal_app LOGIN PASSWORD 'local_app' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE DATABASE portal;
CREATE DATABASE portal_test;
```

Na pasta `apps/api`, configure a URL administrativa apenas para migrações, substituindo `SENHA_LOCAL` pela senha do seu administrador PostgreSQL:

```powershell
$env:DATABASE_URL='postgresql+psycopg://portal_app:local_app@127.0.0.1:5432/portal'
$env:MIGRATION_DATABASE_URL='postgresql+psycopg://postgres:SENHA_LOCAL@127.0.0.1:5432/portal'
../../.venv/Scripts/python.exe -m alembic upgrade head
Remove-Item Env:MIGRATION_DATABASE_URL
$env:ALLOW_DEMO_SEED='true'
$env:DEMO_PASSWORD='DemoEscolar2026!'
../../.venv/Scripts/python.exe -m app.seed
../../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8100
```

Em outro terminal, na pasta `apps/web`:

```powershell
npm.cmd ci
$env:API_URL='http://127.0.0.1:8100'
$env:APP_ORIGIN='http://localhost:3100'
npm.cmd run dev -- --hostname 127.0.0.1
```

No Linux/macOS, use `python3.14`, `.venv/bin/python` e `export NOME=valor`; remova variáveis com `unset`. Para testes backend nativos, aponte ambas as URLs para `portal_test`, defina `TEST_DATABASE_ALLOWED=true`, `ALLOW_DEMO_SEED=true` e `DEMO_PASSWORD`, aplique a migração e rode `python -m pytest -q` em `apps/api`.

## API e manutenção

`POST /api/v1/auth/login` recebe JSON `{ "email": "...", "password": "..." }` e retorna a sessão opaca. No Swagger, copie `access_token` para **Authorize**; as próximas chamadas usam Bearer. `GET /api/v1/me` informa as instituições autorizadas. Operações escolares usam `/api/v1/institutions/{institution_id}/...`. As credenciais administrativas do banco nunca são usadas pelo serviço API.

Examine falhas de inicialização com `docker compose logs migrate seed api web`. Para parar preservando o banco: `docker compose down`. Volumes persistem; não remova volumes sem entender que isso elimina seus cadastros locais.

Ao alterar models, crie uma **nova** migração. Não altere a migração `0001` já aplicada. Dependências estão fixadas em `requirements.txt` e `package-lock.json`; atualizações exigem repetir testes e build. Dados reais, recuperação de senha, OIDC/MFA, operação multiunidade, observabilidade e proteção de produção permanecem sujeitos às próximas etapas e à revisão de segurança.

## Pesquisa e benchmarking

- [Pesquisa Aprofundada: Funcionalidades, Inovações e Tendências em Apps de Gestão Escolar (2024–2026)](pesquisa_funcionalidades_apps_gestao_escolar.md)
