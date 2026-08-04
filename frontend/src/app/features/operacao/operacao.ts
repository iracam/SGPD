import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MessageModule } from 'primeng/message';
import { finalize } from 'rxjs';

import { AjudaLink } from '../../core/ajuda/ajuda-link';
import { errorMessage } from '../../core/api/api-error';
import { Operacao } from './models/operacao.models';
import { OperacaoService } from './operacao.service';

/**
 * Operação e monitoramento do ambiente (R63, RNF-009).
 *
 * A fila de avisos só anda quando o agendador do sistema operacional chama os
 * comandos (ADR-049). Se ele parar, nada quebra e ninguém é avisado — esta
 * tela é onde isso fica visível. Ela não envia, não reprocessa e não apaga:
 * lê e dá o veredito.
 */
@Component({
  selector: 'app-operacao-page',
  imports: [DatePipe, MessageModule, RouterLink, AjudaLink],
  templateUrl: './operacao.html',
  styleUrl: './operacao.scss',
})
export class OperacaoPage {
  private readonly service = inject(OperacaoService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly operacao = signal<Operacao | null>(null);
  protected readonly carregando = signal(true);
  protected readonly erro = signal('');

  constructor() {
    this.service
      .estado()
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => this.operacao.set(result),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível ler o estado da operação.')),
      });
  }

  /** Enum cru nunca chega ao usuário (ADR-047). */
  protected rotuloSituacao(status: string): string {
    return (
      {
        PENDENTE: 'Pendente',
        ENVIANDO: 'Em envio',
        ENVIADA: 'Enviada',
        FALHA: 'Falha',
        CANCELADA: 'Cancelada',
      }[status] ?? status
    );
  }

  protected estadoDoChip(status: string): string {
    return (
      {
        PENDENTE: 'pending',
        ENVIANDO: 'review',
        ENVIADA: 'released',
        FALHA: 'blocked',
        CANCELADA: 'canceled',
      }[status] ?? 'pending'
    );
  }

  protected situacoes(counts: Record<string, number>): string[] {
    return Object.keys(counts).sort();
  }

  protected tamanho(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    const mib = bytes / (1024 * 1024);
    if (mib < 1) {
      return `${(bytes / 1024).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} KiB`;
    }
    return `${mib.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MiB`;
  }
}
