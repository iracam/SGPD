/** Manuais operacionais servidos por `apps.core.views.manual`. */
export type ManualSlug =
  | 'primeiros-passos'
  | 'responsaveis-de-area'
  | 'departamento-pessoal'
  | 'grupos-templates-regras'
  | 'usuarios-e-auditoria'
  | 'configuracao-do-sistema';

/**
 * O `slug` precisa existir na lista branca do backend (`OPERATION_MANUALS`) e o
 * arquivo correspondente em `docs/operacao/`. A `secao` é o `id` de um `h2` do
 * manual gerado — ela evita abrir o documento na capa quando a dúvida é sobre
 * uma tela específica.
 */
export interface AjudaDestino {
  slug: ManualSlug;
  secao?: string;
}
