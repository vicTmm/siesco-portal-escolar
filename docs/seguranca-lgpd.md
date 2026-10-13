# Segurança e proteção de dados

Plano de controles para implementação, não declaração de conformidade já alcançada. Base consultada em 13/10/2026: [texto compilado da LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm). As finalidades, bases legais e prazos de guarda devem ser definidos pela instituição e revisados com sua assessoria antes de dados reais.

## Governança

Proposta: instituição decide finalidades acadêmicas como controladora; fornecedor SaaS atua como operador nessas operações. Dados de contratação e segurança da própria plataforma podem ter papéis distintos, documentados por finalidade. Contrato deve estabelecer instruções, suboperadores, confidencialidade, suporte a direitos, incidentes, encerramento e devolução/eliminação de dados.

Manter inventário de tratamento: categoria, titular, finalidade, base legal, campos mínimos, destinatários, localização, retenção e responsável. Não usar consentimento genérico para todas as operações. Para crianças e adolescentes, observar melhor interesse, linguagem adequada e requisitos específicos do art. 14; definir a base aplicável à finalidade. Consentimento, quando usado, precisa ser verificável e revogável, sem impedir serviços essenciais indevidamente. Arts. 6, 7, 11, 14, 18, 37 e 46 orientam a revisão de princípios, bases, dados sensíveis, menores, direitos, registros e segurança.

## Dados e minimização

| Categoria | Tratamento proposto |
| --- | --- |
| Identidade e contato | Coletar apenas o necessário à matrícula e comunicação; CPF não obrigatório no MVP básico |
| Notas e frequência | Acesso por vínculo e finalidade; snapshots publicados; sem ranking público |
| Relações familiares | Verificação pela secretaria, validade e restrições; mudanças auditadas |
| Saúde, deficiência e documentos judiciais | Fora do MVP básico; se necessários, módulo restrito com base e finalidade próprias |
| Credenciais e tokens | Não registrar em logs; tokens de backend somente no servidor |
| Telemetria | Request_id e métricas agregadas; sem conteúdo acadêmico ou identificadores desnecessários |

Não incluir publicidade comportamental, rastreamento de menores ou treinamento de modelos com dados escolares. Analytics externo não é requisito do portal, mesmo que esteja referenciado no site público analisado.

## Controles técnicos

- TLS em produção e criptografia de banco, backups e armazenamento; gestão de chaves separada e rotação documentada.
- OIDC/PKCE, sessões HttpOnly e MFA para contas privilegiadas; rate limit em login e recuperação; mensagens que não revelam existência da conta.
- Autorização por ação e objeto, RLS por tenant, FKs compostas e conta de runtime sem bypass. Testar também exports, jobs, caches e downloads.
- Cookies Secure/SameSite, validação Origin e token CSRF em mutações; CORS restrito se acesso direto à API for introduzido. CSP e escape de conteúdo; diário usa texto simples no MVP.
- Limites de payload, paginação, tempo de execução e upload. Arquivos futuros: tipo/tamanho permitidos, verificação de malware, chave imprevisível e bucket privado.
- Segredos em serviço apropriado na produção; nenhum token em URL, Git ou mensagens de erro. Rotação e privilégios mínimos para CI, migração e backup.
- Atualizações de dependências, análise de vulnerabilidades e revisão de mudanças de autenticação/permissão antes de liberar.

## Auditoria

Registrar alterações de matrícula, vínculo familiar, permissões, frequência, notas, políticas, fechamento, reabertura e publicação; registrar exports, acesso de suporte e tentativas proibidas com payload mínimo. Ator, tenant/escola, instante UTC, ação, objeto, resultado, request_id e motivo são obrigatórios quando aplicáveis.

Eventos de mutação são inseridos na mesma transação. Conta de runtime pode inserir eventos, mas não atualizá-los ou excluí-los. Consulta é restrita; logs técnicos não substituem auditoria de domínio. Correções de notas têm histórico protegido, separado de logs gerais. Cópia periódica para armazenamento protegido aumenta resistência a adulteração; monitorar lacunas e alterações administrativas. Retenção dos eventos deve ser definida, sem prometer imutabilidade absoluta apenas pelo uso de tabela append-only.

Administrador SaaS não consulta dados escolares por padrão. Suporte tem concessão aprovada, finalidade, expiração, escopo e registro de acessos; acesso emergencial exige procedimento institucional e revisão posterior, sem conta compartilhada.

## Direitos, retenção e encerramento

Canal institucional recebe solicitações, verifica identidade e representação, registra pedido, responsável e prazo aplicável. Exportação e resposta não incluem terceiros sem fundamento. Correção cadastral é direta quando autorizada; correção acadêmica segue revisão e histórico. Eliminação exige avaliar obrigações de guarda e direitos de outras pessoas; quando não puder ser atendida, registrar e comunicar justificativa.

Definir tabela de retenção antes do piloto para cadastro, documentos, histórico acadêmico, sessões, logs, backups e auditoria, com fundamento e evento inicial do prazo. Não fixar um prazo universal para documentos escolares. Soft delete não resolve retenção: job controlado realiza anonimização/eliminação quando cabível, respeitando bloqueio legal. Backups expiram por ciclo definido; restauração deve reaplicar eliminações posteriores e revogações antes de reabrir acesso.

Encerramento de tenant: bloquear novos usos conforme contrato, exportar dados em formato documentado para destinatário autorizado, verificar entrega e executar política de retenção/eliminação, preservando somente o devido. Transferência internacional e suboperadores precisam de avaliação específica antes da contratação.

## Incidentes e continuidade

Manter contatos de plantão, classificação, contenção, preservação de evidência, avaliação de titulares afetados e comunicação coordenada com a controladora. Prazos e critérios de notificação à ANPD/titulares devem seguir regulamentação vigente e ser verificados antes da entrada em produção; não depender somente do art. 48 ou de prazo presumido. Operador deve informar a controladora rapidamente conforme contrato e fornecer evidências suficientes.

Backups criptografados, acesso segregado, PITR e ensaio de restauração com dados sintéticos. Proposta de RPO ≤ 15 min e RTO ≤ 4 h depende de infraestrutura e ensaio. Registrar resultado real, falhas e plano de correção. Preparar indisponibilidade de provedor OIDC e PostgreSQL, sem criar acesso alternativo inseguro.

## Verificações de liberação

1. Matriz tenant/escola/perfil/objeto passa, inclusive responsável revogado e professor sem atribuição.
2. Reuso de conexão não mantém contexto anterior; conta de aplicação não contorna RLS.
3. Publicação, correção e reabertura preservam histórico; rascunhos não chegam às famílias.
4. Logs e erros não contêm CPF, tokens, notas ou documentos desnecessários.
5. Restauração, resposta a incidente e solicitação de titular são demonstradas.
6. Inventário, bases legais, retenção, contratos e contatos estão aprovados pela instituição piloto.
