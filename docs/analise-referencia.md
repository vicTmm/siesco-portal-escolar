# Análise da referência pública

Data da inspeção: 13/10/2026. Referência: https://www.intersystem.eti.br/.

## Método e limitações

O MCP REA informado pelo solicitante não está exposto no catálogo de ferramentas desta sessão. Portanto, esta análise **não foi realizada com REA**. Foi possível consultar páginas via ferramenta web e HTTP GET e inspecionar referências do HTML e configurações do JavaScript público. A tentativa de abrir o navegador integrado falhou com “Browser is not available: iab”. Não houve validação visual, execução de interações, captura de tráfego em runtime nem inspeção de telas autenticadas. Uma revisão com REA continua pendente quando o conector estiver acessível.

Somente URLs públicas presentes nos links e recursos do site foram consultadas. Não foram enviados formulários, realizadas autenticações, enumeradas rotas privadas ou tentados contornos de acesso. Não foram incorporados código, imagens, logotipos, textos comerciais ou identidade visual ao projeto. Os scripts foram lidos apenas para caracterizar comportamento, sem reproduzir sua implementação.

## Registro de evidências

| ID | URL | Resultado observado | Alcance |
| --- | --- | --- | --- |
| E01 | https://www.intersystem.eti.br/ | HTTP 200; conteúdo comercial, artigos, contatos e links externos | HTML e texto público |
| E02 | https://www.intersystem.eti.br/about-us.html | Página institucional, equipe e descrição geral de gestão acadêmica e financeira | Texto público |
| E03 | https://www.intersystem.eti.br/contact.html | HTTP 200; seções de localização, telefone e e-mail | HTML; a ferramenta web falhou, mas GET direto funcionou |
| E04 | https://www.intersystem.eti.br/new-oportunidades.html | HTTP 200; artigo editorial | HTML; sem relação operacional comprovada com portal |
| E05 | https://www.intersystem.eti.br/new-pandemia.html | HTTP 200; artigo editorial | HTML público |
| E06 | https://www.intersystem.eti.br/assets/js/main.js | HTTP 200; handlers de menu/rolagem e inicializações de plugins | Inspeção estática, não execução |

## Navegação e componentes

E01–E05 mostram uma estrutura de site institucional: início, apresentação da empresa, contato e artigos, com rodapé compartilhando contatos e links externos. Há referências a WhatsApp, e-mail, mapa, Bússola, acesso gratuito e um endereço externo `/professor` em isiweb.com.br. Esses destinos foram identificados, mas seus produtos e funcionalidades não foram examinados. A referência ao acesso gratuito não autoriza afirmar que existe uma demonstração aberta do iSapiens.

No HTML há botão de navegação com atributos de collapse do Bootstrap. As páginas têm títulos, imagens, blocos de apresentação e rodapé. Isso descreve sua estrutura, sem atestar layout responsivo ou acessibilidade em execução.

## Recursos JavaScript e comportamentos

E01 referencia jQuery 1.12.4, Modernizr 3.6.0, Bootstrap, Popper, Slick, Isotope, imagesLoaded, Magnific Popup, counterUp, Waypoints, WOW, circle-progress, nice-select e `main.js`. Também há referência ao carregamento do Google tag/Analytics. São dependências do site público; não permitem deduzir a stack do produto escolar. Links para Angular, Flutter, .NET e SQL Server são referências institucionais, não prova de tecnologias efetivamente usadas no backend.

E06 contém handlers de clique para navegação, tratamento de rolagem, inicializações Slick para vários seletores, filtros Isotope, pop-ups de vídeo/imagem, contadores, seleção estilizada e botão de retorno ao topo. **Observação estática:** há configuração desses comportamentos. **Hipótese:** os elementos correspondentes podem usar essas interações quando presentes. Não se confirmou que todos os seletores existam nas páginas nem que os plugins funcionem sem erros. Dependências antigas justificam estudar uma implementação própria atual, sem inferir vulnerabilidades do produto.

## Funcionalidades: graus de comprovação

| Tema | Evidência | Classificação |
| --- | --- | --- |
| Gestão acadêmica e financeira; públicos administrativo, docente e discente | Descrição institucional E02 | Alegação pública verificada como texto; operação não demonstrada |
| Relatórios, análise gerencial, acesso web/móvel e comunicação com famílias | Apresentação E01 | Alegação pública; fluxos não testados |
| Mesclagem de dados em documentos Google Docs | Descrição do complemento em E01 | Alegação pública; integração não executada |
| Contato e leitura de artigos | Links e páginas E01–E05 | Recursos públicos observados |
| Matrículas, turmas, disciplinas, diário, notas, frequência e boletim | Nenhuma tela ou fluxo observado | Propostas deste projeto, motivadas pelo pedido |
| Cobranças, pagamentos, biblioteca, transporte, LMS e integrações oficiais | Sem fluxo observado | Possíveis módulos futuros, não atribuíveis à referência |

Nenhuma funcionalidade educacional transacional foi efetivamente testada. A confirmação de uma descrição comercial não equivale à confirmação operacional. A proposta nos demais documentos é independente da implementação do fornecedor.

## Próxima inspeção quando REA estiver disponível

Repetir E01–E06, registrar viewport e versão da ferramenta; confirmar menu, navegação, carrosséis, retorno ao topo, teclado e estados de carregamento. Registrar URLs finais, screenshots autorizados e recursos carregados, distinguindo evidência runtime de leitura estática. Parar em qualquer barreira de autenticação e não coletar dados pessoais. Só ampliar conclusões educacionais mediante demonstração pública ou ambiente explicitamente autorizado.
