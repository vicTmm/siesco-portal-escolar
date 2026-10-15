# Psicologia escolar e NFS-e

Escopo ajustado em 15/10/2026 conforme decisões do usuário.

## Decisões de produto

- Cobrança, garantias de inadimplência e operação jurídica das mensalidades continuam no **Isaac**. Gateway Pix/boleto/cartão, conciliação de pagamentos e negociação com juros não são pendências do SIESCO.
- **Transporte por rotas foi retirado do escopo.** A opção foi ocultada dos serviços; registros históricos existentes foram preservados.
- Carteira/cantina/loja usam saldo interno com crédito manual; não houve contratação de gateway ou integração com o Isaac.
- Inscrição pública significa captação de interessados por formulário sem login, anterior à matrícula. Foi explicada ao usuário, mas ainda não foi priorizada ou implementada.
- Referência de produto: **iSapiens**, conforme informado pelo usuário. Ainda não há login fornecido para mapear sua interface; esta entrega usa fluxos próprios e documentação oficial.

## Psicologia

Perfil próprio `psychologist`, criado pela direção em Contas e permissões. O profissional registra atendimento realizado, tipo (acolhimento, acompanhamento, avaliação, família ou encaminhamento), observações, análise, plano, registro profissional opcional e próximo retorno. A direção consulta; somente o psicólogo autor acrescenta evoluções/retificações e anexos.

- Consultas, evoluções e anexos cifrados com `APP_ENCRYPTION_KEY`; título e nomes de anexos genéricos.
- Família, aluno, professores, coordenação e secretaria não consultam o conteúdo, inclusive por URL direta ou anexos.
- Outro psicólogo não recebe automaticamente os registros do autor. Direção consegue consultar o histórico mesmo após revogar o perfil profissional.
- Conteúdo original é imutável; correções são complementos no histórico. O banco também bloqueia sobrescrita da consulta. Evoluções usam versão para evitar repetição concorrente.
- Acesso auditado e restrito à unidade selecionada; MFA de equipe inclui psicologia quando obrigatório na instalação.
- Não são gerados diagnósticos, recomendações clínicas ou compartilhamentos automáticos com famílias/equipe.

Demonstração local: `psychologist@aurora.example.com`, senha `asd123`. O seed adiciona esse perfil nas duas instituições fictícias sem redefinir senhas existentes. Contas reais continuam exigindo senha forte.

## NFS-e de serviços

Escola informada: Engenho Pequeno, **São Gonçalo/RJ**. O portal municipal informa que a emissão migrou ao padrão nacional em 2026; o ISS Online permanece para consultas. A integração foi preparada para o **Emissor Público Nacional**, sem depender de login no iSapiens.

Fluxo disponível para direção/secretaria:

1. Direção preenche CNPJ, razão social, município, inscrição municipal quando exigida, série exclusiva da DPS, numeração, serviço e enquadramento confirmados com o contador. Homologação é o ambiente inicial.
2. Escola escolhe aluno e responsável com vínculo verificado, CPF/CNPJ do tomador, endereço, competência, descrição e valor em reais.
3. Plataforma cria rascunho privado, reserva a numeração e preserva um retrato do cadastro fiscal. Versão impede preparar usando cadastro alterado por outra pessoa. A chave de idempotência evita duplicar o mesmo pedido.
4. Ao emitir, valida o layout XSD da DPS, assina com certificado RSA vinculado ao CNPJ e envia por mTLS ao endpoint oficial. Identificador e XML assinado são gravados antes da comunicação externa.
5. Autorização exige retorno oficial com XML válido, chave, ambiente/CNPJ corretos e DPS equivalente à declaração assinada. Isso impede associar uma nota antiga de outro tomador que use a mesma série/número.
6. Timeout/interrupção mantém resultado a confirmar. A consulta usa a mesma DPS, recupera chave/XML e não gera outra numeração. Apenas resposta de DPS não encontrada permite reenviar os mesmos bytes.
7. XML autorizado é preservado cifrado e imutável, com download autenticado. Notas de homologação são destacadas como **sem validade fiscal**; número oficial da NFS-e é distinto da série/número da DPS.

### Ativação pendente

**Não houve emissão real nem homologação externa. O regime tributário real da escola ainda não foi confirmado.** A escola não forneceu certificado ou parâmetros fiscais reais. Os testes locais usam certificado sintético e respostas oficiais simuladas, sem transmitir dados à Receita/prefeitura. Sem configuração válida, o botão retorna impedimento de configuração; não inventa número, chave ou autorização.

Para ativar, o contador/operador deve configurar certificado ICP-Brasil A1 e chave PEM privada, cadastro/habilitação do contribuinte, códigos, enquadramento, série exclusiva do SIESCO e sequência compatível com o emissor já utilizado. Primeiro homologar; produção só fica liberada quando o mapa privado da instalação indicar `production_enabled: true` para aquele CNPJ. Não envie certificado, senha ou chave pelo chat/GitHub.

O processo da API lê `NFSE_CERTIFICATES_FILE`, um JSON privado por **ID de unidade**, com o seguinte formato ilustrativo:

```json
{
  "ID-DA-UNIDADE": {
    "cnpj": "CNPJ-REAL-DA-ESCOLA",
    "certificate": "/run/secrets/nfse/escola-cert.pem",
    "private_key": "/run/secrets/nfse/escola-key.pem",
    "production_enabled": false
  }
}
```

Compose monta `NFSE_SECRETS_DIR` em `/run/secrets/nfse`, somente leitura. O padrão local é `.local/nfse-secrets`, ignorado pelo Git. Garanta leitura apenas ao operador e usuário de execução da API. Certificado expirado, chave incompatível, CNPJ sem correspondência e produção não liberada impedem envio. O certificado pode corresponder à raiz do CNPJ, conforme vínculo de configuração. Preserve a chave de criptografia da aplicação para ler XML/cadastros no backup.

### Limites fiscais atuais

Emissão inicial contempla tomador nacional, CPF/CNPJ numérico, operação tributável sem retenções/deduções/benefícios e sem regime especial; Simples ME/EPP com apuração conjunta no Simples. Outras operações, não optantes pelo Simples/MEI, CNPJ alfanumérico, regimes híbridos/especiais, imunidade, retenções, complementos IBS/CBS exigidos para o caso concreto, substituição/cancelamento e geração de DANFSe/PDF fiscal precisam de desenvolvimento/homologação adicionais. O contador deve confirmar que a operação da escola cabe no fluxo antes de ativar. Não há cálculo/inferência automática de enquadramento ou tributos. Serviço existente no iSapiens não confirma elegibilidade da configuração no SIESCO.

A série/numeração não deve colidir com o emissor anterior ou outra unidade com o mesmo CNPJ. Rascunhos preservam a numeração reservada; rejeições exigem novo rascunho corrigido. Consulta de DPS inexistente permite reenvio da mesma declaração, não edição do documento assinado.

Sem dados fiscais reais, não é correto apresentar a emissão como homologada ou apta à produção.

## Referências oficiais

- [Aviso de São Gonçalo/RJ](https://sistema.pmsg.rj.gov.br/pmsaogoncalo/issonline/iss.login.php)
- [Manuais e esquemas nacionais vigentes](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/documentacao-atual)
- [Ambientes oficiais de API](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/apis-prod-restrita-e-producao)
- Esquemas incorporados e normalização pontual de compatibilidade XSD: `apps/api/app/assets/nfse/README.md`.

## Verificação

Testes cobrem separação de perfis e unidades, revogação, conteúdo clínico cifrado/imutável, anexos privados, numeração e idempotência fiscal, certificado vinculado, bloqueio de produção não configurada, assinatura, XML conforme XSD, autorização simulada e consulta após timeout. As contagens finais estão no tracking. A verificação local não substitui homologação do contribuinte no emissor oficial.
