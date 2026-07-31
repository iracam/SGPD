import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MessageModule } from 'primeng/message';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { DecisaoValor, PendenciaStatus } from '../tarefas/models/tarefas.models';
import { ConsolidacaoValores } from './models/processo-valores.models';
import { ProcessoValoresService } from './processo-valores.service';

/**
 * Conferência somente leitura das pretensões do processo (RF-026).
 *
 * A tela não decide nada: a decisão vive em `Minhas tarefas`, sob a segregação
 * da ADR-048. Aqui o `DP` soma, confere e vê separadas as decisões tomadas por
 * quem informou o valor.
 */
@Component({
  selector: 'app-processo-valores-page',
  imports: [DatePipe, RouterLink, MessageModule],
  templateUrl: './processo-valores.html',
  styleUrl: './processo-valores.scss',
})
export class ProcessoValoresPage {
  private readonly service = inject(ProcessoValoresService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  readonly consolidacao = signal<ConsolidacaoValores | null>(null);
  readonly carregando = signal(true);
  readonly erro = signal('');

  constructor() {
    const uuid = this.route.snapshot.paramMap.get('uuid') ?? '';
    this.service
      .consolidar(uuid)
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => this.consolidacao.set(result),
        error: (error) =>
          this.erro.set(
            errorMessage(error, 'Não foi possível carregar a consolidação de valores.'),
          ),
      });
  }

  protected valorFormatado(value: string | null, currency: string): string {
    if (value === null) {
      return '—';
    }
    return `${currency} ${Number(value).toLocaleString('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  protected rotuloDecisao(decision: DecisaoValor): string {
    return {
      APROVADA_COBRANCA: 'Aprovada para cobrança',
      REJEITADA: 'Rejeitada',
      ABONADA: 'Abonada',
    }[decision];
  }

  protected rotuloStatus(status: PendenciaStatus): string {
    return {
      ABERTA: 'Aberta',
      EM_REGULARIZACAO: 'Em regularização',
      REGULARIZADA: 'Regularizada',
      ENCAMINHADA_ANALISE: 'Encaminhada para análise',
      CONTESTADA: 'Contestada',
      APROVADA_COBRANCA: 'Aprovada para cobrança',
      REJEITADA: 'Rejeitada',
      ABONADA: 'Abonada',
      ENCERRADA: 'Encerrada',
    }[status];
  }

  protected estadoStatus(status: PendenciaStatus): string {
    return {
      ABERTA: 'blocked',
      EM_REGULARIZACAO: 'pending',
      REGULARIZADA: 'released',
      ENCAMINHADA_ANALISE: 'review',
      CONTESTADA: 'review',
      APROVADA_COBRANCA: 'released',
      REJEITADA: 'canceled',
      ABONADA: 'canceled',
      ENCERRADA: 'canceled',
    }[status];
  }
}
