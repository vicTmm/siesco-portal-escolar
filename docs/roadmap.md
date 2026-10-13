# Roadmap incremental

O status vivo das entregas e o requisito de acesso online 24/7 ficam em [tracking.md](tracking.md). Atualizar esse acompanhamento a cada entrega.

Sequência por dependência, sem estimativas de prazo antes de validar equipe e escola piloto. A primeira implementação cobre parcialmente esta sequência; consulte [implementacao-v1.md](implementacao-v1.md) para o escopo entregue, testes executados e pendências. Cada incremento futuro deve ser pequeno, demonstrável com dados sintéticos de dois tenants e revisado antes da próxima expansão.

| Entrega | Escopo | Critérios objetivos de aceitação |
| --- | --- | --- |
| 0 — Descoberta | Revisar estes documentos e regras da escola piloto | Definir segmento, tenant/unidades, transferência, escala, arredondamento, recuperação, frequência, publicação e retenção; registrar decisões e exemplos de cálculo; listar pendência REA explicitamente |
| 1 — Fundação local | Next.js/TS/Tailwind/shadcn, FastAPI, PostgreSQL, Compose, migrações e CI | Um comando sobe serviços saudáveis em checkout limpo; migração cria banco vazio; seed tem dois tenants; CI passa lint/typecheck e smoke; nenhum segredo no Git |
| 2 — Identidade | OIDC, sessão, logout e contexto | Login/logout funcionam; cookie seguro em produção; MFA de equipe demonstrado; sessão revogada deixa de acessar; seleção de tenant inválido negada; CSRF bloqueado em mutações |
| 3 — Tenant e escola | Bootstrap, membros, perfis e RLS | API e consulta SQL com papel de runtime negam tenant alheio; ausência de contexto não revela linhas; teste sequencial reutiliza conexão entre A/B sem vazamento; escola não concedida negada; admin SaaS não lê boletins |
| 4 — Pessoas | Aluno, responsável e verificação do vínculo | Cadastro sem login é possível; FK entre tenants rejeitada; responsável não verificado não acessa aluno; revogação bloqueia acesso imediatamente; mutações auditadas sem dados sensíveis em logs |
| 5 — Organização acadêmica | Ano, período, disciplinas, currículo e turma | Datas inválidas rejeitadas; códigos duplicados no escopo rejeitados; turma possui ofertas e professor; versão de currículo usado não é alterada retroativamente |
| 6 — Matrícula | Ativação e alocação inicial | Duplicidade por aluno/escola/ano rejeitada; repetição idempotente não duplica; capacidade respeitada sob concorrência; relações incompatíveis de ano/escola negadas |
| 7 — Movimentação | Mudança de turma e cancelamento | Troca encerra/inicia intervalos sem sobreposição; falha reverte ambas as mudanças; status tem histórico; vínculo fora da data não recebe chamada; matrícula anterior é preservada |
| 8 — Diário e chamada | Aula, conteúdo e frequência em lote | Professor de outra oferta recebe negação; chamada inválida reverte lote inteiro; ausência de lançamento aparece como pendência; aula cancelada não conta; versão concorrente causa conflito |
| 9 — Avaliações e notas | Avaliação, lançamento e cálculo preliminar | Notas fora da escala rejeitadas; pendente não vira zero; exemplos homologados têm resultado exato; edição concorrente detectada; mudança de nota produz auditoria |
| 10 — Fechamento | Revisão, publicação e reabertura | Pendências impedem fechar; turma fechada rejeita mutação; reabertura sem motivo/aprovação negada; nova publicação mantém snapshot anterior; cálculo agrega movimentações sem duplicar |
| 11 — Portal | Boletim e frequência publicados | Aluno vê apenas sua matrícula; responsável vê apenas vínculos vigentes; rascunho invisível; teste troca tenant/escola/aluno e não encontra vazamento; leitura em celular e teclado validada |
| 12 — Piloto seguro | Observabilidade, backup, direitos e operação | Restauração ensaiada e tempos medidos; teste de carga cumpre meta acordada; fluxo de correção/exportação de dados com identidade verificada demonstrado; logs sem tokens/CPF; plano de incidentes exercitado |
| 13 — Expansão | Avisos, documentos e relatórios em entregas separadas | Avisos chegam apenas ao público autorizado; download/export exige autorização na execução e leitura; arquivos são privados e links expiram; cada módulo passa matriz de acesso própria |

## Definição de concluído

Cada entrega inclui migração quando aplicável, contrato OpenAPI atualizado, documentação de operação, demonstração do caso feliz e dos casos de negação relevantes. Testes de integração usam PostgreSQL real para constraints/RLS; testes de UI cobrem somente fluxos críticos. Não substituir testes de autorização por ocultação de botão.

Dados reais só entram depois da entrega 12 e da homologação das regras acadêmicas, contrato de tratamento, retenção, responsáveis operacionais e treinamento. A introdução de dados deve ser pequena e conciliada com a secretaria; migração em massa é projeto separado.

## Riscos e decisões abertas

- REA não acessível: análise runtime pendente, sem bloquear arquitetura independente.
- Segmento e regras locais ainda não confirmados: fechar na entrega 0, antes de codificar cálculos.
- Identidade: selecionar provedor OIDC, custos e região; planejar recuperação segura de contas de menores.
- Instituições com exigência de banco dedicado: avaliar impacto contratual e operacional antes de onboarding.
- Histórico e transferências: homologar equivalências de disciplina/escala antes de automatizar resultado.
- Retenção, exportação, infraestrutura e suboperadores: validar com responsáveis institucionais antes do piloto.
