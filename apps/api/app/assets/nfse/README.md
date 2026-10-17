Esquemas oficiais do Sistema Nacional NFS-e, pacote NFSe-ESQUEMAS_XSD-v1.01-20260209, consultado em 15/10/2026.

Fonte: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/documentacao-atual
Pacote: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/nfse-esquemas_xsd-v1-01-20260209.zip

Os arquivos são preservados sem alterações. Na validação em runtime, o único facet de série que usa âncoras PCRE (`^0{0,4}\d{1,5}$`) é normalizado para a restrição numérica equivalente do XSD 1.0 (`0{0,4}[0-9]{1,5}`), pois `^`/`$` são literais no validador XSD. As demais regras oficiais são mantidas. A série também é limitada na API a 1–49999. Atualizações do layout precisam de homologação explícita; não há download automático em runtime.
