# Avisos por WhatsApp — proposta e demonstração

Registro da conversa de 14/10/2026 para implementação futura.

## Escopo acordado

A escola tem em média 350 alunos e pretende enviar para um responsável por aluno. A secretaria seleciona turmas/turnos, prepara uma mensagem uma vez e envia individualmente aos responsáveis. Estimativa: 15 avisos mensais; se todos receberem todos os avisos, 5.250 mensagens/mês. O consumo da API será repassado sem margem; desenvolvimento e manutenção são separados.

Tarifas de referência consultadas: utilidade R$ 0,0350 (R$ 183,75/mês) e marketing R$ 0,3217 (R$ 1.688,925, arredondado a R$ 1.688,93/mês). Não são preços contratados: confirmar tabela oficial, moeda de faturamento, impostos, intermediários e classificação dos modelos na ativação. A tabela detalhada oficial bloqueou a consulta automatizada; valores foram obtidos em referência secundária: https://gwhats.com/en/precos-api-whatsapp . Regras gerais: https://whatsappbusiness.com/products/platform-pricing/ .

## Versão mock

Menu “Avisos por WhatsApp”, acessível aos gestores já habilitados no portal. Base própria fictícia de 350 alunos em dez turmas, com autorização simulada. Filtros por turno e múltiplas turmas, exclusão individual de destinatários, composição, prévia individual, estimativa por aviso e por 15 avisos, revisão com confirmação e resultado/histórico simulados. Nenhuma chamada à Meta ou ao backend de cadastros. Histórico apenas em memória enquanto a tela estiver montada; troca de instituição ou saída da tela o apaga. Os exemplos de modelos não foram submetidos nem aprovados. Não conectar o texto livre demonstrativo diretamente à produção.

## Implementação real futura

- Usar WhatsApp Cloud API oficial. Primeiro testar com número de teste da Meta, celular do desenvolvedor como destinatário verificado e token temporário.
- Preferir conta empresarial, número e cobrança pertencentes à escola, com acesso técnico para manutenção. Aplicativo WhatsApp Business não é requisito da Cloud API. Se o número já está no aplicativo, validar elegibilidade para coexistência/migração antes de alterar o cadastro.
- Configurar credenciais de produção somente no servidor, número verificado, pagamento, nome de exibição e verificação empresarial quando exigida.
- Fora da janela de 24 horas após uma mensagem do responsável, usar modelos aprovados. Não presumir que “Comunicado: {{texto}}” permite conteúdo arbitrário nem que todo aviso escolar será utilidade. Validar dois ou três modelos reais e classificação antes de fechar orçamento.
- Coletar e registrar autorização: texto aceito, data, responsável e origem. Telefone na matrícula sozinho não basta. Oferecer saída e bloquear novos disparos para quem cancelou. Exemplo: “Quero receber pelo WhatsApp avisos sobre a rotina escolar do aluno enviados pela Escola [nome], como alterações de horário e lembretes. Posso cancelar esse recebimento a qualquer momento.”
- Pais usam WhatsApp normal; não precisam entrar em grupo nem salvar o número. Pode-se coletar adesão no portal/matrícula ou divulgar formulário/QR code por canal existente.
- Integrar matrículas ativas, turmas/turnos, responsável principal e telefone normalizado; eliminar duplicidades por número em avisos comuns e não enviar para pessoas sem autorização.
- Implementar fila, limites da conta, idempotência, retentativas e webhooks autenticados para estados de entrega, mensagens recebidas e cancelamento. Registrar custos reais por mensagem entregue; simulação não comprova entrega ou leitura.
- Planejar atendimento às respostas dos pais, controle de acesso por instituição, proteção dos dados e trilha de auditoria.

Política: https://whatsappbusiness.com/policy/ . Início: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started .
