import { NgClass } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ButtonModule } from 'primeng/button';

import { AuthService } from '../auth/auth.service';
import { ThemeService } from '../theme/theme.service';
import { LayoutService } from './layout.service';
import { NavItem } from './layout.types';

@Component({
  selector: 'app-authenticated-layout',
  imports: [NgClass, RouterLink, RouterLinkActive, RouterOutlet, ButtonModule],
  templateUrl: './authenticated-layout.html',
  styleUrl: './authenticated-layout.scss',
})
export class AuthenticatedLayout {
  protected readonly authService = inject(AuthService);
  protected readonly layoutService = inject(LayoutService);
  protected readonly themeService = inject(ThemeService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  /** Gaveta do estado base; irrelevante a partir de `lg`. */
  protected readonly mobileNavOpen = signal(false);

  protected readonly navItems: NavItem[] = [
    {
      label: 'Painel',
      route: '/fe/painel',
      icon: 'pi pi-th-large',
      description: 'Visão geral dos processos demissionais',
    },
    {
      label: 'Colaboradores',
      route: '/fe/colaboradores',
      icon: 'pi pi-id-card',
      description: 'Consulta cadastral no Senior HCM',
      feature: 'query_senior_references',
    },
    {
      label: 'Setores',
      route: '/fe/setores',
      icon: 'pi pi-building',
      description: 'Setores de validação, prazos e escopos de atendimento',
      feature: 'manage_sectors',
    },
    {
      label: 'Responsáveis',
      route: '/fe/responsaveis',
      icon: 'pi pi-user-plus',
      description: 'Usuários, setores, escopos e validade das responsabilidades',
      feature: 'manage_sectors',
    },
    {
      label: 'Usuários',
      route: '/fe/usuarios',
      icon: 'pi pi-users',
      description: 'Contas, senhas e vínculo com o Active Directory',
      feature: 'manage_users',
    },
    {
      label: 'Auditoria',
      route: '/fe/auditoria',
      icon: 'pi pi-history',
      description: 'Trilha de eventos de contas',
      feature: 'view_account_audit',
    },
  ];

  protected readonly configurationNavItem: NavItem = {
    label: 'Configurações',
    route: '/fe/configuracoes',
    icon: 'pi pi-cog',
    description: 'Configurações técnicas exclusivas de SuperAdmin',
  };

  protected readonly visibleNavItems = computed(() =>
    this.navItems.filter((item) => !item.feature || this.authService.canView(item.feature)),
  );
  protected readonly showConfigurationSection = computed(
    () =>
      this.authService.currentUser()?.is_superuser ??
      this.authService.currentContext()?.scopes.is_superuser ??
      false,
  );

  constructor() {
    if (!this.authService.currentContext()) {
      this.authService
        .loadContext()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({ error: () => undefined });
    }
  }

  protected toggleNav(): void {
    this.layoutService.toggleNav();
  }

  protected toggleMobileNav(): void {
    this.mobileNavOpen.update((open) => !open);
  }

  protected closeMobileNav(): void {
    this.mobileNavOpen.set(false);
  }

  protected openPasswordPage(): void {
    this.closeMobileNav();
    void this.router.navigateByUrl('/fe/senha');
  }

  protected toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  protected logout(): void {
    this.closeMobileNav();
    this.authService
      .logout()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => void this.router.navigateByUrl('/fe/login'),
        error: () => void this.router.navigateByUrl('/fe/login'),
      });
  }
}
