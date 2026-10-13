# Módulos e permissões

Todos os módulos são propostas próprias. A referência pública não demonstrou seus fluxos transacionais. Perfil é um conjunto de ações; autorização sempre combina ação + tenant + escola + objeto + vínculo vigente + estado acadêmico. Negar por padrão, inclusive em exports e jobs. Interface oculta ações indisponíveis, mas a API é a autoridade.

## Escopo incremental

| Módulo | Entrega mínima | Dependências |
| --- | --- | --- |
| Plataforma | Instituições, status e bootstrap do primeiro diretor | Identidade e auditoria |
| Identidade | Login, logout, escolha de contexto, convites, MFA e revogação | Provedor OIDC |
| Pessoas | Alunos, profissionais, responsáveis e vínculo verificado | Tenant/escola |
| Acadêmico | Ano/períodos, etapas, disciplinas, currículo e turmas | Cadastros |
| Matrícula | Matrícula, alocação, cancelamento e movimentação com histórico | Pessoas e acadêmico |
| Diário | Aulas, conteúdo, chamada e pendências | Matrícula e atribuição docente |
| Avaliação | Avaliações, notas, políticas e fechamento | Diário e períodos |
| Portal | Boletim e frequência publicados; filhos autorizados | Vínculos e resultados |
| Auditoria | Registro transacional e consulta restrita | Transversal desde a fundação |
| Comunicação | Avisos por público, publicação e leitura | Posterior ao MVP |
| Documentos/relatórios | Exports privados, emissão e histórico | Posterior ao MVP |

Financeiro, pagamentos, biblioteca, transporte, LMS, aplicativos nativos, integração Google Docs e integrações governamentais ficam fora do MVP. Cada expansão terá descoberta própria; não prometer equivalência ao iSapiens.

## Matriz de acesso inicial

| Perfil | Escopo | Ações permitidas | Restrições |
| --- | --- | --- | --- |
| Administrador da plataforma | Catálogo SaaS | Criar/suspender tenant, operação técnica | Sem leitura automática de dados escolares; suporte por concessão |
| Diretor | Escolas concedidas | Gestão de equipe, visão acadêmica, aprovação de políticas e reabertura | Sem acesso a outras unidades ou tenant; não redefine notas silenciosamente |
| Coordenador pedagógico | Escolas concedidas | Currículo, atribuições, revisão do diário, políticas propostas, fechamento/publicação | Correções pós-fechamento exigem reabertura aprovada |
| Secretaria | Escolas concedidas | Pessoas, vínculos, matrículas, movimentação e documentos autorizados | Não lança notas nem muda política de avaliação |
| Professor | Ofertas atribuídas e período vigente | Aulas, frequência, avaliações e notas dos participantes | Sem acesso a alunos não atribuídos, dados financeiros ou resultados fechados |
| Aluno | Pessoa e matrículas próprias | Leitura de resultados publicados e avisos destinados | Sem dados dos colegas, rascunhos ou alteração acadêmica |
| Responsável | Alunos com vínculo pedagógico verificado e vigente | Leitura de resultados publicados e avisos destinados | Sem acesso por mera declaração de parentesco ou vínculo financeiro |

Pessoas podem acumular perfis. Permissões concedidas se somam, mas isolamento, vínculo, bloqueio judicial e estado fechado continuam restrições obrigatórias. Mudança de escola/contexto nunca reutiliza autorização do contexto anterior. Um professor que também é responsável acessa cada finalidade em contexto apropriado.

## Navegação própria proposta

Após login: seletor de instituição/escola somente para vínculos existentes. Navegação por tarefas: Pessoas, Organização acadêmica, Matrículas, Diário, Avaliações, Portal e Administração, conforme permissão. Professor entra por suas turmas/ofertas; aluno por sua matrícula; responsável por aluno vinculado. Administração da plataforma fica em área separada.

Telas devem prever vazio, carregamento, erro, edição concorrente e confirmação de mudanças de alto impacto. Listas não expõem CPF, informações médicas ou contatos familiares sem finalidade. UX móvel para chamada e boletim, teclado, foco visível, mensagens de validação e rótulos acessíveis.

## Fluxo mínimo completo

Secretaria cadastra aluno/responsável e verifica vínculo → coordenação configura ano, turma, disciplina, professor e política → secretaria efetiva matrícula → professor registra aula, chamada e notas → coordenação resolve pendências, fecha e publica → aluno/responsável consulta boletim. Cancelamento e transferência mantêm histórico; correção após fechamento cria reabertura e nova publicação auditadas.
