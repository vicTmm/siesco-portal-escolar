# Operação e ativação de produção

## Situação

A interface e a API funcionam localmente. `compose.prod.yaml` prepara banco privado, migração, API, interface e Caddy com HTTPS. Não há hospedagem contratada, domínio apontado, provedor de e-mail ou monitor externo configurados nesta entrega. Configuração preparada não equivale a serviço disponível 24/7.

## Publicação

1. Escolher servidor/serviço gerenciado, região, orçamento e domínio. Instalar Docker/Compose no servidor e apontar DNS para ele.
2. Criar arquivo de ambiente privado fora do Git. Definir `PORTAL_DOMAIN`, `ACME_EMAIL`, senhas novas `POSTGRES_PASSWORD` e `POSTGRES_APP_PASSWORD` (codificar caracteres reservados em URLs), `APP_ENCRYPTION_KEY`, SMTP e política de backups. Não reutilizar valores de `.env.example`, `.local` ou a senha `asd123`.
3. Gerar a chave MFA: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Guardar a chave em cofre separado do banco e incluir sua recuperação no plano de incidentes. Sem ela os segredos TOTP existentes não podem ser lidos. Rotação exige procedimento de recriptografia; não basta trocar a variável.
4. Executar `docker compose --env-file /caminho/privado.env -f compose.prod.yaml config --quiet`, depois `up --build -d`. O ambiente de produção não executa seed.
5. Criar o primeiro administrador com `docker compose ... run --rm -e BOOTSTRAP_ADMIN_EMAIL -e BOOTSTRAP_ADMIN_PASSWORD api python -m app.bootstrap`, exportando as duas variáveis no terminal. O bootstrap recusa alterar administradores existentes e exige 16 caracteres.
6. Entrar por HTTPS, configurar MFA em Minha senha e guardar códigos de recuperação. Produção exige MFA para plataforma/equipe antes de liberar operações administrativas. Escolha de provedor OIDC/SSO permanece decisão externa; esta entrega oferece autenticação local com MFA, sem afirmar integração OIDC.
7. Configurar SMTP (STARTTLS), testar convite e recuperação com caixa autorizada. Links usam `PUBLIC_APP_URL` e expiram em 30 minutos. `.eml` local é apenas para desenvolvimento, não envio real.
8. Homologar perfis, regras de notas, fechamento e acesso familiar em uma instituição piloto com dados sintéticos antes da entrada de dados reais.

## Backup e restauração

- `infra/ops/backup.sh`: usa `BACKUP_DATABASE_URL` e `BACKUP_DIR`; gera dump customizado privado e verifica seu catálogo.
- `infra/ops/restore-drill.sh`: usa `RESTORE_DATABASE_URL` e `BACKUP_FILE`; recusa bancos diferentes de `portal_restore` ou com tabelas existentes. Não apaga dados. Criar antes o banco vazio com credencial de operação.
- Incluir certificados/configurações, chave MFA e segredos no plano de recuperação, separados e protegidos; o dump do banco sozinho não restaura tudo.
- Agendar execução externa (scheduler/cron do servidor), cópia criptografada fora do servidor, retenção e alertas após escolher infraestrutura. Esses serviços não estão ativos.
- Ensaio realizado em 15/10/2026: dump do banco local e restauração transacional em `portal_restore`; versão 0005 e quatro instituições fictícias recuperadas. Contagens de contas, alunos, aulas, notas, publicações por período/anuais e alocações coincidiram com a origem; RLS permaneceu ativa sem contexto. Repetir em produção com volume e infraestrutura reais. Isso não comprova RPO/RTO de produção.

## Disponibilidade e incidentes

`infra/ops/healthcheck.sh` consulta `PORTAL_URL` e `API_HEALTH_URL`, falhando com código não zero quando algum serviço estiver indisponível. Em produção, `/health` público é encaminhado à API, incluindo teste de conexão ao banco. Conectar um monitor externo e seus alertas depois de escolher o serviço; o script não dispara mensagens sozinho.

Definir com a escola meta de disponibilidade, RPO, RTO, retenção, responsável de plantão, canal de suporte e janela de manutenção. Diante de falha: conferir health/containers, preservar logs sem tokens, diagnosticar conexão/migração/capacidade, restaurar apenas para banco separado e validar antes de substituir o serviço. Incidentes envolvendo dados exigem fluxo institucional próprio.

## Proteções implementadas e limites

- Isolamento por instituição com RLS, autorização por perfil/vínculo, referências compostas e papel de runtime sem bypass.
- Nonce de scripts por resposta e CSP; estilos inline continuam permitidos por compatibilidade com React/Radix. Cache privado, proteção contra enquadramento e política de referenciador sem envio.
- Sessão HttpOnly/Secure, CSRF por Origin, revogação após senha/MFA e limitação de tentativas persistida no banco.
- MFA TOTP com proteção contra repetição, segredos cifrados e oito códigos de recuperação armazenados como hashes e consumidos uma vez. Base técnica: [RFC 6238](https://www.rfc-editor.org/rfc/rfc6238) e [Fernet](https://cryptography.io/en/latest/fernet/).
- Auditoria transacional de mutações e exportações; sem payload pessoal nos logs de erro. Motivos de movimentação e reabertura ficam em registros separados, restritos à instituição.
- Recuperação de senha depende de caixa de e-mail confiável; não desativa MFA. Se perder também os códigos de recuperação, definir procedimento institucional de identificação e intervenção autorizada, sem bypass automático.
- Testes locais não substituem revisão externa de segurança, definição legal de retenção/base de tratamento, direitos dos titulares, proteção operacional contra abuso e teste de carga com metas acordadas. Esses itens dependem de responsáveis e infraestrutura reais.

## Expansão dos serviços escolares

A versão 0016 acrescenta dados privados, carteira/estoque, documentos, notificações e sincronização offline. Preserve `APP_ENCRYPTION_KEY` no backup; a chave protege MFA e conteúdos clínicos/PEI/retiradas. A migração 0014 usa a chave para converter avisos médicos preexistentes e falha caso precise dela e ela esteja ausente. O serviço de migração recebe a mesma chave da API. Homologue restauração, permissões e carga da versão atual antes de uso real. Detalhes e limites em [expansao-pesquisa.md](expansao-pesquisa.md).
