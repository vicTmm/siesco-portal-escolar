# Organização acadêmica — ACA-01

Entrega de 13/10/2026. Este documento complementa o registro histórico implementacao-v1.md: calendários, períodos e currículos agora estão implementados. Diário, frequência, avaliações e boletim continuam nas próximas etapas.

## Uso no portal

1. Entre como diretor ou coordenador e abra **Anos letivos**. Cadastre nome, número do ano e datas inicial/final. Os calendários podem atravessar o ano civil.
2. Em **Períodos letivos**, selecione o calendário e defina nome, sequência e datas de cada bimestre, trimestre ou semestre. A nomenclatura e quantidade são escolhas da escola (até 24 períodos).
3. Cadastre disciplinas. Em **Currículos**, crie código, nome, etapa e versão. A combinação código/versão é única na escola.
4. Em **Matriz curricular**, selecione o currículo em rascunho e inclua disciplinas e carga horária inteira (1 a 3000 horas por componente). Componentes podem ser editados ou removidos enquanto estiver em rascunho.
5. Volte a **Currículos** e use **Publicar**. Um currículo vazio não pode ser publicado. A publicação protege esta versão e suas disciplinas contra edição/exclusão; para alterações, cadastre outra versão.
6. Crie a turma com um ano letivo já cadastrado. Opcionalmente, selecione um currículo publicado da mesma etapa. Após o vínculo, essa turma mantém a versão escolhida. Atribuições docentes devem usar disciplinas da matriz vinculada.

Secretaria tem acesso de consulta. Professores, alunos e responsáveis continuam no portal por vínculo. A API aplica essas permissões independentemente dos controles visuais.

## Regras e preservação de histórico

- Datas são inclusivas: dois períodos não podem compartilhar nem mesmo o dia de início/fim. Exemplo válido: primeiro termina em 15/04 e segundo começa em 16/04.
- Períodos devem caber no calendário e acompanhar a ordem da sequência; nome e sequência não se repetem no mesmo calendário.
- Alterar o calendário não pode deixar períodos existentes fora de suas datas. Número do ano é fixo; o período não muda de ano depois de criado.
- Código e número da versão do currículo são fixos. Publicar novamente a mesma versão já publicada é idempotente e não duplica auditoria.
- A API trava o calendário durante mudanças de períodos e o currículo durante mudanças/publicação da matriz. Triggers reforçam limites e imutabilidade no PostgreSQL.
- Todas as tabelas novas têm RLS e FKs compostas por instituição/escola. Mutações e auditoria são confirmadas na mesma transação.
- Vincular currículo a uma turma existente exige que suas atribuições atuais pertençam à matriz. Currículo vinculado não pode ser removido ou substituído.
- Turmas sem currículo são preservadas durante a transição. Uma etapa posterior pode exigir matriz em todas as turmas antes da operação acadêmica completa.

## Migração 0002

Execute `alembic upgrade head` com a credencial administrativa de migração, conforme o README. Não altere 0001, não remova volumes e não recrie o banco.

Para cada ano já utilizado nas turmas, a migração cria um calendário de 01/01 a 31/12 com **Revisar datas importadas**. Essas datas são provisórias e não representam calendário homologado. Abra **Editar**, informe as datas reais e salve; o aviso passa a **Datas definidas**. Nenhum período, currículo ou política de avaliação é inventado pela migração. Alunos, turmas e matrículas são preservados.

Em bancos novos, o seed usa calendário fictício de 2026. O seed continua idempotente e não altera dados já existentes.

## API

Prefixo: `/api/v1/institutions/{institution_id}`. Listagens aceitam `limit` de 1 a 100 e `offset` não negativo.

| Recurso | Operações |
| --- | --- |
| `/academic-years` | GET, POST; PUT em `/{id}` |
| `/academic-terms` | GET, POST; PUT em `/{id}` |
| `/curricula` | GET, POST; PUT em `/{id}`; POST em `/{id}/publish` |
| `/curriculum-subjects` | GET, POST; PUT e DELETE em `/{id}` |
| `/classes` | Agora valida ano cadastrado e aceita `curriculum_id` opcional |
| `/assignments` | Agora valida se a disciplina pertence ao currículo vinculado à turma |

O contrato de campos está no OpenAPI da API. Datas inválidas e relações incompatíveis retornam 422; duplicidades, sobreposição ou alterações em histórico protegido retornam 409. IDs fora do escopo autorizado retornam 404.

## Validação

- 44 testes de backend aprovados em PostgreSQL 18, com papel de runtime sem superuser/BYPASSRLS.
- 13 testes de frontend/BFF aprovados, incluindo API real; build de produção e TypeScript aprovados.
- Seis cenários E2E originais e novo cenário acadêmico aprovados com Chrome/API reais. O novo cenário usa datas futuras, valida sobreposição, publicação e seleção da versão na turma.
- Migração: downgrade para 0001 e reaplicação em portal_test preservaram IDs de alunos/turmas/matrículas; calendários importados sinalizados. `alembic check` sem alterações pendentes.
- Revisão visual de capturas desktop/móvel. Capturas locais não entram no Git.
- CI anterior aprovada; execução local de containers ainda pendente por ausência do daemon Docker.

Regras institucionais de avaliação, fechamento, calendário final e retenção seguem para homologação antes de dados reais.
