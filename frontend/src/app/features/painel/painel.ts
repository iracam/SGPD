import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MessageModule } from 'primeng/message';
import { finalize } from 'rxjs';

import { AjudaLink } from '../../core/ajuda/ajuda-link';
import { errorMessage } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { ScopeAssignment } from '../../core/auth/models/auth.models';
import { Indicadores, TotalMoeda } from './models/painel.models';
import { PainelService } from './painel.service';

/**
 * Painel de operação (RF-034, RF-035).
 *
 * Cada bloco vem por capacidade, não por papel declarado: o backend devolve
 * `null` no que não se aplica ao ator. A tela não soma nem filtra nada — todo
 * número é calculado no servidor, sobre a mesma visibilidade que as listagens
 * de processos e de tarefas já usam.
 */
@Component({
  selector: 'app-painel-page',
  imports: [DatePipe, MessageModule, RouterLink, AjudaLink],
  templateUrl: './painel.html',
  styleUrl: './painel.scss',
})
export class PainelPage {
  protected readonly authService = inject(AuthService);
  private readonly service = inject(PainelService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly indicadores = signal<Indicadores | null>(null);
  protected readonly carregando = signal(true);
  protected readonly erro = signal('');

  constructor() {
    this.service
      .indicadores()
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => this.indicadores.set(result),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar os indicadores.')),
      });
  }

  /**
   * Enum cru nunca chega ao usuário (ADR-047). O contexto publica os cinco
   * códigos atribuíveis do catálogo (ADR-054) já expandidos pela implicação,
   * mais a capacidade derivada do vínculo de setor.
   */
  protected rotuloPapel(role: string): string {
    return (
      {
        DP: 'Departamento Pessoal',
        DP_GERENTE: 'Gerência do Departamento Pessoal',
        GRUPOS_TEMPLATE_ADMIN: 'Administração de grupos e templates',
        SETORES_ADMIN: 'Administração de setores',
        USUARIOS_ADMIN: 'Administração de usuários',
        RESPONSAVEL_SETOR: 'Responsável de setor',
      }[role] ?? role
    );
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

  protected estadoDoChip(status: string): string {
    return (
      {
        RASCUNHO: 'pending',
        INICIADO: 'review',
        LIBERADO_PARA_RESCISAO: 'released',
        RESCISAO_PROCESSADA: 'released',
        ENCERRADO: 'released',
        CANCELADO: 'canceled',
      }[status] ?? 'pending'
    );
  }

  protected valorFormatado(total: TotalMoeda): string {
    return `${total.currency} ${Number(total.informed).toLocaleString('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }
}
