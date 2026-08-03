import { Component, computed, input } from '@angular/core';
import { ButtonModule } from 'primeng/button';

import { ManualSlug } from './ajuda.types';

/**
 * Atalho para o manual operacional da tela, aberto em aba nova.
 *
 * Aba nova e não modal: `X_FRAME_OPTIONS = DENY` impede enquadrar o documento
 * em um iframe, mesmo sendo da mesma origem, e um manual de vinte páginas se lê
 * melhor ao lado do sistema do que dentro dele.
 *
 * O destino é servido por `apps.core.views.manual`, que exige sessão — o mesmo
 * cookie da SPA acompanha a navegação, então a aba nova abre autenticada.
 */
@Component({
  selector: 'app-ajuda-link',
  imports: [ButtonModule],
  templateUrl: './ajuda-link.html',
  styleUrl: './ajuda-link.scss',
})
export class AjudaLink {
  /** Manual a abrir. Precisa existir na lista branca do backend. */
  readonly manual = input.required<ManualSlug>();

  /** `id` de um `h2` do manual gerado; sem ele o documento abre na capa. */
  readonly secao = input<string>();

  readonly rotulo = input('Ajuda');

  protected readonly url = computed(() => {
    const secao = this.secao();
    return `/ajuda/${this.manual()}/${secao ? `#${secao}` : ''}`;
  });

  protected readonly descricaoAcessivel = computed(
    () => `${this.rotulo()} — abre o manual desta tela em uma aba nova`,
  );
}
