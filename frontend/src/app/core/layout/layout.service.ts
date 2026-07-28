import { Injectable, signal } from '@angular/core';

import { STORAGE_KEYS } from '../auth/auth.constants';

/**
 * Estado da navegação. O colapso só tem efeito a partir de `lg`: abaixo disso a
 * navegação é uma gaveta sobreposta (ADR-028).
 */
@Injectable({ providedIn: 'root' })
export class LayoutService {
  readonly navCollapsed = signal(this.readCollapsed());

  toggleNav(): void {
    const next = !this.navCollapsed();
    this.navCollapsed.set(next);
    this.persist(next);
  }

  private readCollapsed(): boolean {
    if (typeof localStorage === 'undefined') {
      return false;
    }
    return localStorage.getItem(STORAGE_KEYS.navCollapsed) === 'true';
  }

  private persist(value: boolean): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(STORAGE_KEYS.navCollapsed, String(value));
  }
}
