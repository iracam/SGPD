import { Component, inject } from '@angular/core';

import { AuthService } from '../../core/auth/auth.service';
import { ScopeAssignment } from '../../core/auth/models/auth.models';

@Component({
  selector: 'app-painel-page',
  imports: [],
  templateUrl: './painel.html',
  styleUrl: './painel.scss',
})
export class PainelPage {
  protected readonly authService = inject(AuthService);

  /** Enum cru nunca chega ao usuário (ADR-047). */
  protected rotuloPapel(role: string): string {
    return { DP: 'Departamento Pessoal' }[role] ?? role;
  }

  protected registroEscopo(scope: ScopeAssignment): string {
    if (scope.scope_type === 'GLOBAL') {
      return 'Todas as empresas';
    }
    if (scope.scope_type === 'COMPANY') {
      return `Empresa ${scope.company_code}`;
    }
    return `Empresa ${scope.company_code} · Filial ${scope.branch_code}`;
  }
}
