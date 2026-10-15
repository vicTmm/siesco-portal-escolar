# Diário, avaliações e boletins

## Fluxo implementado

1. Cadastrar calendário, períodos, turma, disciplina, professor e atribuição docente.
2. Em **Diário e avaliações**, direção/coordenação cria uma regra e abre um diário por atribuição/período. Não há regra acadêmica aplicada automaticamente.
3. Professor acessa somente suas atribuições. Registra aula por data e número da aula, faz chamada em lote e cria avaliações. Direção/coordenação também podem lançar; secretaria consulta.
4. Notas vazias e chamadas não preenchidas são pendências. Valores fora da escala da avaliação são rejeitados; lotes inválidos são revertidos integralmente. A versão do diário evita sobrescrita concorrente.
5. Direção/coordenação revisa resultados, fecha e publica. Pendências impedem fechar; fechamento impede novas alterações. Reabertura exige direção e justificativa registrada. Cada publicação guarda notas, frequência e regra em snapshot preservado.
6. Alunos e responsáveis com vínculo verificado consultam somente publicações. Reabertura mantém a publicação anterior visível até uma nova publicação. Revogação do vínculo bloqueia imediatamente a leitura.

## Regras oferecidas

São modelos iniciais editáveis pela escola, não afirmações sobre uma regra obrigatória do mercado:

| Modelo | Fórmula do período |
| --- | --- |
| Média simples | Média de `(nota / máximo da avaliação) × escala` |
| Média ponderada | `soma(nota / máximo × peso) / soma(pesos) × escala` |
| Soma de pontos | `soma(notas) / soma(máximos) × escala` |
| Conceitos | Média simples proporcional, convertida por faixas percentuais definidas pela escola |

Sugestões iniciais: escala 0–10 ou 0–100; conceitos A/B/C/D. A escola escolhe escala, mínimo, frequência, casas decimais e faixas. Arredondamento convencional (`ROUND_HALF_UP`) com Decimal; nenhuma nota ausente vira zero. Regras ficam imutáveis; mudanças exigem criar outra regra e escolher em novos diários.

Recuperação: sem recuperação; maior entre média e recuperação; substituição; ou média das duas. A avaliação de recuperação é exigida apenas para aluno cuja média esteja abaixo do mínimo; uma recuperação por diário. O resultado permanece pendente enquanto essa recuperação obrigatória não estiver lançada. Notas são registradas numericamente também no modelo de conceitos; a conversão ocorre no resultado.

Frequência: cada aula equivale a uma ocorrência. Presente conta como presença; ausente e falta justificada contam como ausência. Aula cancelada não entra no cálculo. A escola precisa validar essa convenção antes de adotar a regra. Regras de abono por justificativa e aulas com duração variável não estão configuradas nesta versão.

## Consolidação anual

Em **Consolidação anual**, direção/coordenação escolhe calendário, regra de escala/aprovação/recuperação e peso de cada período. Pesos iguais fazem média simples; diferentes fazem média ponderada. Todos os períodos devem estar cadastrados antes de salvar; os períodos desse calendário ficam protegidos depois de fixar a regra anual.

A consolidação usa a última publicação de cada diário. Períodos ausentes continuam pendentes. Quando há mudança de turma na mesma disciplina/período, combina os resultados proporcionalmente ao número de aulas cursadas; soma as aulas e ausências para frequência. A composição das disciplinas vem de atribuições e do currículo publicado quando existir. Considera apenas períodos que se sobrepõem aos intervalos de matrícula.

Recuperação final, quando exigida pela regra, é informada por disciplina antes de publicar. Publicações anuais preservam fontes, regra e revisão. Republicar cria nova revisão; não apaga a anterior. Equivalências entre escolas/escalas diferentes e conselho de classe precisam de homologação específica e não são inferidos.

## Movimentação

Em **Matrículas → Movimentar / histórico**, secretaria/direção escolhe troca de turma, cancelamento/transferência externa ou reativação; informa data e motivo de pelo menos dez caracteres. Cada intervalo é fechado antes do próximo iniciar, sem sobreposição. A data final é exclusiva. Mesmo ano letivo, capacidade e isolamento são validados; a matrícula original não é removida.

Movimentações retroativas com aulas/avaliações já registradas a partir da data são bloqueadas para impedir reescrita silenciosa da população do diário. Essa versão exige conciliação desses registros antes da movimentação. Migração de matrículas anteriores reconstrói início pelo calendário; a escola deve revisar esse histórico antes de usar dados reais.

## Acesso e relatórios

- **Minha senha**: troca com senha atual, encerrando sessões; MFA TOTP opcional em desenvolvimento e obrigatório para equipe na configuração de produção.
- **Esqueci minha senha** e **Enviar convite**: token de 30 minutos, uso único, guardado como hash. Link usa fragmento (`#reset_token=`), que não é enviado ao servidor no endereço da requisição. SMTP precisa ser configurado; modo local grava `.eml` privado em `.local/mail`.
- **Busca global**: pessoas/turmas/disciplinas; cadastros por nome também buscam em todas as páginas. Portal familiar tem busca e paginação próprias.
- **Auditoria**: direção consulta eventos paginados. Motivos ficam no histórico da movimentação e no registro de reabertura.
- **Relatórios**: direção/secretaria exporta alunos, turmas e matrículas em CSV autorizado, com proteção contra fórmulas em células. Boletim publicado pode ser impresso. Emissão de documentos oficiais assinados/anexos privados não faz parte desses relatórios iniciais.

## Próximas ativações externas

Ver [operacao-producao.md](operacao-producao.md) para hospedagem, HTTPS, SMTP, backups e monitoramento. OIDC/SSO depende de provedor escolhido. WhatsApp real foi adiado pelo usuário em 15/10/2026; lembrar da configuração da Meta após as demais entregas, conforme [whatsapp-avisos.md](whatsapp-avisos.md).
