# Expansão a partir da pesquisa

Implementação de 15/10/2026. Os fluxos abaixo persistem no PostgreSQL e têm regras de acesso por instituição, unidade, perfil e aluno. A pesquisa continua sendo uma visão mais ampla do produto; os limites estão registrados nesta página.

## Como demonstrar

Acesse http://localhost:3100. Contas locais: `director@aurora.example.com`, `secretary@aurora.example.com`, `teacher@aurora.example.com` e `guardian@aurora.example.com`; senha local de demonstração: `asd123`. Use dados sintéticos. Cada perfil apresenta as opções permitidas.

1. **Mural**: escolha ano, turma/turno ou aluno; publique aviso, enquete ou autorização. Entre como responsável para confirmar leitura e responder. A direção acompanha recibos e decisões. Autorizações têm finalidade específica: geral, imagem, medicamento ou retirada. Confirmação de aluno/professor não substitui leitura do responsável.
2. **Documentos**: emita declaração, frequência, boletim por período ou histórico anual publicado. Baixe o PDF, abra o QR e compare o arquivo na página pública. O hash é calculado no navegador. Minutas de contrato usam modelos publicados pela direção e dados de um responsável verificado; são identificadas como **sem assinatura**.
3. **Serviços**: atendimento por setor, expediente, calendário, matrícula/rematrícula, CRM, planos, questões, PEI, saúde, biblioteca, transporte, financeiro, achados e perdidos, momentos e orientações. Cada serviço tem campos próprios, comentários, anexos, versões e transições permitidas.
4. **PEI e saúde**: a direção concede acesso por profissional/aluno/categoria. Cadastre metas com alvo, unidade, prazo e evolução; registre ocorrências de enfermaria. Medicação requer receita anexada e autorização específica vigente para agendar/registrar administração. Não há cálculo de dose nem prescrição pelo sistema.
5. **Carteira e loja**: cadastre produtos, preço e estoque; registre crédito manual, consumo na cantina, compra familiar na loja, entrega ou estorno. A família consulta extrato e define limite diário e etiquetas bloqueadas. Saldo e estoque são conferidos na mesma transação; repetir a mesma operação não duplica o lançamento.
6. **Portaria**: gere identificação escolar temporária; equipe confere presencialmente e registra entrada. Para terceiro, a família informa pessoa, vínculo, documento e autorização de retirada; o QR tem validade e uso único. A fila permite chegada manual ou conferência de proximidade por localização consentida; a liberação continua sendo presencial.
7. **Agenda e notificações**: abra horários de reunião, reserve para aluno vinculado e consulte lembretes no sino. Há lembretes internos de avisos, comentários, vencimentos financeiros, livros, medicação, reuniões e chamada da fila. O expediente controla alertas da equipe; famílias podem enviar solicitações fora do horário.
8. **Diário offline**: em `/offline`, prepare um diário com conexão, abra sem rede, guarde aulas/chamada e reconecte. Divergências exigem revisão e seleção explícita do que reaplicar; a versão anterior fica no histórico local. Sessão expirada preserva rascunhos até reautenticação. Sair explicitamente remove as cópias locais.
9. **Apoio pedagógico**: alertas explicáveis de média/frequência e faltas consecutivas; comparativo de turma em boletins quando há pelo menos cinco resultados numéricos completos; banco próprio de questões; montagem de provas com ordem opcionalmente aleatória, figuras e PDF de gabarito separado; correção de respostas digitadas.
10. **Grade e unidades**: gere proposta semanal sem conflito de turma/professor/sala, considerando indisponibilidade docente. Crie unidades e escolha unidade/perfil no seletor superior. Contas existentes podem ganhar outro perfil sem outra senha; cadastros das unidades ficam separados.

## Escopo e limites

| Área | Entregue | Limite atual |
| --- | --- | --- |
| Atendimento | Setores com permissões, expediente, comentários atualizados periodicamente, anexos e notificações internas | Sem presença online, WebSocket, push ou envio externo |
| Matrícula/rematrícula | Família complementa dados/documentos de aluno já cadastrado e vinculado; escola analisa | Aprovação não efetiva matrícula, pagamento ou assinatura; secretaria conclui o cadastro acadêmico. Sem inscrição pública anônima |
| CRM | Contatos e funil novo/contatado/matriculado/encerrado | Conversão e contatos externos manuais |
| Planejamento | Data, habilidades BNCC informadas, objetivos, atividades, recursos e publicação | Sem catálogo oficial importado ou geração por IA |
| Questões e provas | Banco próprio, revisão, figuras, prova congelada, PDFs separados e correção digitada | Sem importação licenciada, OCR/câmera ou lançamento automático de notas |
| PEI | Plano, metas estruturadas, progresso numérico/evidências, publicação e concessões de acesso | Sem perfil próprio de terapeuta externo; profissionais usam perfis existentes com concessão explícita |
| Saúde | Ficha, enfermaria e medicação com receita/autorização vigente | Registro informado pela escola; sem prescrição, cálculo de dose ou integração clínica |
| Biblioteca | Exemplares, reserva, empréstimo, devolução/extravio e lembretes internos | Sem entrega de e-mail/push; exemplar não pode ter dois empréstimos/reservas ativos |
| Transporte | Rotas e registros manuais de embarque/desembarque | Sem GPS contínuo ou aplicativo de motorista |
| Financeiro | Recebíveis, baixa manual, lembretes internos e negociação com simulação exata de parcelas | Simulação sem juros; aprovação substitui recebíveis pendentes uma vez. Sem gateway, conciliação ou cobrança externa |
| Cantina/carteira | Crédito manual, extrato, limite diário, bloqueio por etiquetas, consumo e estorno de compra | Sem recarga por Pix/cartão; restrições são configuradas explicitamente, sem inferir alergias da ficha médica |
| Loja/eventos | Catálogo, estoque, checkout pelo saldo interno, pedidos, entrega e estorno | Sem pagamento externo, frete ou gestão fiscal |
| Portaria | Identificação temporária, entrada registrada, retirada com documento/autorização e QR único; fila com proximidade | Conferência humana obrigatória; sem catraca, biometria, câmera ou rastreamento em segundo plano |
| Achados e perdidos | Descrição, localização, fotos e retirada/doação | Conteúdo privado conforme vínculo; sem catálogo público |
| Momentos | Fotos por aluno com autorização de imagem vigente | Sem vídeo/álbum coletivo; upload não identifica pessoas na imagem |
| Contratos | Modelo da escola, preenchimento, PDF preservado e verificação de integridade | Minuta sem assinatura; homologação do conteúdo e assinatura de provedor continuam pendentes |
| Orientações | Conteúdo institucional publicado | Sem chatbot/RAG |
| Grade | Proposta de segunda a sexta por ano/turno, carga e indisponibilidade docente, sem conflitos | Busca limitada a 100 mil passos/150 aulas; sem otimização de janelas, intervalos reais, salas indisponíveis ou publicação automática |
| Offline/PWA | Instalação, diário preparado, aulas/chamada locais cifradas, sincronização e revisão de conflitos | Preparação/revalidação exige conexão; revogação remota é conhecida ao reconectar. Outros módulos exigem rede |

## Acesso e preservação

- Rotas conferem unidade, perfil e vínculos atuais. A API exige seleção explícita de vínculo quando há vários na mesma instituição; escolher um ID de outra pessoa não concede acesso.
- Mural preserva público de alunos e decisões. Texto publicado é imutável; correções exigem nova publicação. Apenas responsável verificado responde a autorização/enquete.
- PEI, saúde, metas, enfermaria, medicação e retiradas usam criptografia de aplicação nos conteúdos privados, comentários e anexos correspondentes. Avisos médicos também têm título/texto cifrados e acesso restrito. Retirar o último perfil profissional desativa suas concessões; a família mantém somente os direitos do próprio vínculo.
- Momentos exigem autorização de imagem vigente sem decisão negativa/retirada de responsável vinculado. Revogação bloqueia leitura e download familiar; escola mantém acesso administrativo.
- Anexos PDF/PNG/JPEG de até 2 MB ficam privados, com verificação de formato/hash e download autenticado. Imagens têm limites de dimensões. Não há scanner antivírus integrado.
- PDFs preservam SHA-256; consulta pública revela somente título, instituição, data, validade e hash. Não revela aluno, notas ou arquivo. QR/hash registram integridade; não são assinatura eletrônica de provedor.
- Carteira guarda lançamentos imutáveis; estorno cria lançamento compensatório. Estoque, saldo, versões e chaves de idempotência impedem reaplicação de uma mesma compra. Créditos são manuais pela equipe.
- Migrações 0006–0016 acrescentam RLS forçada, privilégios mínimos, índices, relações e proteções de conteúdo emitido. Migração 0014 exige a chave existente se houver avisos médicos a converter.
- Preserve `APP_ENCRYPTION_KEY` junto da estratégia de backup. Perder a chave impede ler dados cifrados; trocar a chave exige migração de rotação.
- O service worker guarda a tela offline e arquivos estáticos; respostas privadas da API não entram no cache HTTP. Dados de diário preparados usam IndexedDB cifrado por usuário/dispositivo. Logout explícito limpa esse armazenamento.

## Pendências que continuam abertas

**Integrações externas:** WhatsApp oficial/Meta (adiado pelo usuário; retomar após esta etapa), hospedagem/domínio e SMTP de produção, push/SMS, Pix/boleto/cartão e conciliação, assinatura eletrônica, IA/RAG, OCR, Educacenso em layout homologado e hardware de acesso. Nenhuma delas foi ativada nesta entrega.

**Desenvolvimento adicional:** otimização avançada de grade, inscrição pública de novos alunos, vídeos/álbuns coletivos, perfil dedicado a terapeutas, modelos de juros/encargos de negociação, importação licenciada de questões, aplicativo de motorista com rastreamento contínuo e automações externas. Essas funções não se resumem a informar credenciais.

**Homologação:** regras e documentos da escola, permissões, retenção/LGPD, restauração da versão atual, carga/concorrência operacional e segurança independente antes de uso real. A entrega é demonstrável localmente; não houve publicação externa ou homologação de produção.

## Verificação

Validação local: **81 testes API, 16 frontend/BFF e 12 E2E** aprovados; build, TypeScript e Alembic sem divergências. Backup/restauração da versão 0016 conferiu conteúdo e contagens das 51 tabelas, além de RLS sem contexto. As evidências ficam no tracking e no [PR #3](https://github.com/vicTmm/siesco-portal-escolar/pull/3). Cobertura inclui isolamento entre instituições/unidades, revogação de vínculos/perfis, acesso clínico, consentimentos, imutabilidade, conflitos de versão, reserva duplicada, sincronização idempotente, compras/estornos, retirada única, negociação e separação de prova/gabarito. PDFs e telas têm conferência visual local.
