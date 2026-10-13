# Modelo de dados proposto

Modelo lógico inicial, sem DDL executado. UUIDs como identificadores; datas acadêmicas em `date`, eventos em `timestamptz`, notas em `numeric`, nunca float. Tabelas mutáveis têm `created_at`, `updated_at` e `version`. Não aplicar exclusão em cascata a registros acadêmicos.

## Identidade e autorização

| Entidade | Campos principais e relações |
| --- | --- |
| institution | id, nome, slug único, status, timezone |
| school | id, institution_id, nome, código; único por instituição |
| user_account | id, oidc_issuer, oidc_subject, status; par issuer/subject único; identidade global mínima |
| membership | id, institution_id, user_id, person_id, status; um vínculo por conta/instituição |
| school_role | institution_id, school_id, membership_id, role; único por membro/escola/perfil |
| institutional_role | institution_id, membership_id, role; concessões institucionais explícitas |
| platform_role | user_id, role; sem implicar acesso escolar |
| support_grant | institution_id, school_id opcional, user_id, aprovador, motivo, expiração, ações permitidas |
| web_session | id opaco/hash, user_id, contexto ativo, expiração, revogação; armazenamento de tokens protegido |

`person` é local ao tenant: id, institution_id, nome, nome social opcional, nascimento opcional e contatos necessários. CPF não é obrigatório para uso acadêmico básico; se requerido por finalidade validada, fica protegido e não aparece em logs. `student`, `guardian` e `staff` são especializações 0..1 de person, podendo coexistir. Aluno sem conta de login é permitido. Membership liga conta à pessoa após conferência de identidade.

`student_guardian` liga N:M aluno e responsável dentro do tenant: tipo de vínculo, datas de validade, verificação pela secretaria, permissões pedagógicas e restrições. Vínculo financeiro não concede leitura pedagógica automaticamente. Restrições judiciais precisam de procedimento validado; arquivos comprobatórios são privados e não ficam expostos ao professor. Não existe compartilhamento automático de cadastro entre tenants.

## Estrutura acadêmica

| Entidade | Campos/relações e cardinalidade |
| --- | --- |
| academic_year | institution_id, school_id, nome, início, fim, status; escola 1:N anos |
| academic_term | ano_id, nome, sequência, início, fim, status; ano 1:N períodos |
| grade_level | escola_id, etapa, nome, sequência |
| subject | escola_id, código, nome, ativo |
| curriculum | escola_id, grade_level_id, nome, versão, status |
| curriculum_subject | curriculum_id, subject_id, carga horária; N:M |
| class_group | ano_id, grade_level_id, curriculum_id, código, turno, capacidade |
| class_subject | class_id, subject_id, carga prevista; turma N:M disciplina |
| teaching_assignment | class_subject_id, staff_id, início, fim; N:M professores/ofertas |
| grading_policy | escola_id, versão, escala, arredondamento, pesos, regra de recuperação e frequência mínima |
| class_subject_policy | class_subject_id, grading_policy_id; política imutável após uso |

Currículo publicado é versionado; alteração não muda anos anteriores. Períodos não se sobrepõem dentro do ano quando configurados como etapas sequenciais. Todas as datas devem estar no ano letivo. A versão inicial não pretende atender ensino superior, créditos ou cursos livres sem uma extensão validada.

## Matrícula e movimentação

`enrollment`: institution_id, school_id, student_id, academic_year_id, grade_level_id, número, status (rascunho, ativa, transferida, cancelada, concluída), data de ingresso/saída e motivo. Proposta para o MVP: uma matrícula por aluno/escola/ano; reativação reutiliza matrícula e gera histórico. Número único por escola. Se múltiplos programas forem necessários, incluir programa na unicidade após validar a regra.

`enrollment_event` registra transições de status, ator, motivo e data efetiva. `class_placement` liga matrícula à turma com intervalo `[início, fim)`; uma matrícula tem várias alocações históricas, sem intervalos sobrepostos no MVP. Mudança de turma encerra uma alocação e inicia outra atomicamente, preservando notas e frequência anteriores. Turma, matrícula e ano precisam pertencer à mesma escola/ano/etapa compatível. Verificar capacidade com lock da turma para impedir excedentes concorrentes.

`subject_enrollment` liga matrícula a class_subject com validade e situação; sustenta participação disciplinar e exceções futuras. Sua validade precisa estar coberta pela alocação de turma. Transferência entre escolas cria matrícula na escola destino; transferência entre instituições exige procedimento explícito e não uma FK entre tenants.

## Diário, frequência e avaliação

| Entidade | Dados e regras |
| --- | --- |
| lesson | class_subject_id, data, início opcional, sequência, unidades de aula, conteúdo, status, autor; várias aulas no mesmo dia permitidas |
| attendance | lesson_id, subject_enrollment_id, situação (presente, ausente, justificada), unidades ausentes, autor; único por aula/participação |
| assessment | class_subject_id, term_id, título, data, nota máxima, peso, tipo, status |
| grade_entry | assessment_id, subject_enrollment_id, nota nullable, situação (pendente, avaliada, ausente, dispensada), versão; único por avaliação/participação |
| grade_revision | grade_entry_id, valor anterior/novo protegido, autor, motivo, data |
| term_result | enrollment_id, subject_id, term_id, policy_id, média, frequência, situação, versão, publicado_em |
| report_snapshot | enrollment_id, versão, fechamento, policy_version, resultados e origem dos cálculos; imutável após publicação |
| academic_reopening | período, aprovador, motivo, data, versão anterior; cria novo ciclo de fechamento |

Não marcar presença automaticamente: ausência de lançamento significa pendência, não falta. Aula cancelada não compõe denominador. Frequência usa unidades de aula efetivamente ministradas enquanto o aluno estava vinculado; presença parcial é representada por unidades ausentes. Falta justificada não é automaticamente abonada: o efeito depende da política aprovada. Divisão por zero produz frequência indefinida, nunca 100% presumido.

Nota ausente não equivale a zero. Validar 0 ≤ nota ≤ máximo, peso positivo e participação vigente. MVP pode usar média ponderada normalizada para escala da política: soma(nota/máximo × peso)/soma(pesos elegíveis), com arredondamento definido. Pendências bloqueiam fechamento até resolução; dispensa exige regra explícita para denominador. Recuperação, aprovação e frequência mínima são configuráveis e versionadas, sem fixar regra nacional única. Testar exemplos homologados pela coordenação antes do piloto.

Resultados somam participações históricas na mesma disciplina ao longo de movimentações, sem sobrescrever a origem. Mudanças incompatíveis de escala precisam de regra explícita de equivalência. Publicação exige notas/frequência completas e aprovação; aluno/responsável só vê snapshot publicado. Reabertura é autorizada, motivada e auditada, gera nova versão sem apagar a anterior.

## Entidades complementares

`audit_event`: tenant/escola quando aplicável, ator, ação, tipo/id do objeto, resultado, request_id, instante e motivo; payload minimizado. `outbox_event` e `job`: tenant, escola, tipo, payload mínimo, status, tentativas e idempotência. `document`: tenant/escola, dono, finalidade, chave privada, hash e retenção. `announcement` e `announcement_recipient`: público definido e ciência de leitura, apenas em fase posterior. `privacy_request`: solicitante verificado, tipo, prazo, decisão e justificativa. `retention_rule`: categoria, fundamento, prazo e bloqueio legal. `consent_record` somente para finalidades em que consentimento seja base apropriada, com versão e revogação.

## Integridade e isolamento

Todas as entidades escolares acima carregam institution_id e school_id, mesmo quando tabelas omitem repetição na descrição. Entidades institucionais carregam institution_id. Toda FK tenant-local é composta `(institution_id, id)`; FKs escolares usam `(institution_id, school_id, id)` e referenciam UNIQUE equivalente. Isso impede relações entre escolas/tenants, mesmo que IDs enviados sejam válidos. Referências à identidade global são exceções explícitas, sem dados acadêmicos associados no catálogo global.

Índices começam pelo tenant/escola nos filtros usuais: matrícula por ano/aluno/status, aula por oferta/data, nota por avaliação/participação, auditoria por tenant/data. Constraints de unicidade e checks sustentam o modelo. Intervalos podem usar exclusão GiST para alocação sem sobreposição, com extensão btree_gist em migração; validações entre tabelas pertencem a transações e, onde necessário, triggers revisadas. Evitar UNIQUE global em CPF/e-mail de person, que revelaria presença em outra instituição.

Histórico acadêmico é preservado segundo retenção aprovada. Soft delete não é eliminação LGPD; dados sem obrigação de guarda devem ter processo de exclusão/anonimização efetiva. Ver [seguranca-lgpd.md](seguranca-lgpd.md).
