import { DOCUMENT } from '@angular/common';
import { Injectable, inject, signal } from '@angular/core';

import { STORAGE_KEYS } from '../auth/auth.constants';

type AppTheme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);

  readonly theme = signal<AppTheme>(this.readStoredTheme());

  constructor() {
    this.applyTheme(this.theme());
  }

  toggleTheme(): void {
    const next: AppTheme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    this.applyTheme(next);
    this.persist(next);
  }

  private applyTheme(theme: AppTheme): void {
    this.document.documentElement.classList.toggle('app-dark', theme === 'dark');
    this.document.documentElement.style.colorScheme = theme;
  }

  private readStoredTheme(): AppTheme {
    if (typeof localStorage === 'undefined') {
      return 'light';
    }
    const stored = localStorage.getItem(STORAGE_KEYS.theme);
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }
    return matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  private persist(theme: AppTheme): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(STORAGE_KEYS.theme, theme);
  }
}
