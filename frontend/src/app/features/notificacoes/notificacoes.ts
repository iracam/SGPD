import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MessageModule } from 'primeng/message';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import {
  FilaNotificacoes,
  Notificacao,
  NotificacaoEvento,
  NotificacaoStatus,
} from './models/notificacoes.models';
import { NotificacoesService } from './notificacoes.service';

/** Situações oferecidas no filtro, na ordem em que interessam à operação. */
const SITUACOES: readonly NotificacaoStatus[] = [
  'FALHA',
  'PENDENTE',
  'ENVIANDO',
  'ENVIADA',
  'CANCELADA',
];

/**
 * Painel de operação da fila de notificações (RF-027, R07).
 *
 * A tela não envia nada: o envio é do despachante agendado. Aqui o `DP` vê o
 * que saiu, o que falhou e por quê, e devolve à fila o que desistiu.
 */
@Component({
  selector: 'app-notificacoes-page',
  imports: [DatePipe, MessageModule],
  templateUrl: './notificacoes.html',
  styleUrl: './notificacoes.scss',
})
export class NotificacoesPage {
  private readonly service = inject(NotificacoesService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly situacoes = SITUACOES;
  readonly fila = signal<FilaNotificacoes | null>(null);
  readonly filtro = signal<NotificacaoStatus | ''>('');
  readonly carregando = signal(true);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly expandida = signal('');
  readonly reprocessando = signal('');

  constructor() {
    this.carregar();
  }

  protected carregar(): void {
    this.carregando.set(true);
    this.erro.set('');
    this.service
      .listar(this.filtro())
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (fila) => this.fila.set(fila),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar a fila de notificações.')),
      });
  }

  protected filtrar(status: NotificacaoStatus | ''): void {
    this.filtro.set(status);
    this.carregar();
  }

  protected alternar(uuid: string): void {
    this.expandida.set(this.expandida() === uuid ? '' : uuid);
  }

  protected reprocessar(notificacao: Notificacao): void {
    this.aviso.set('');
    this.erro.set('');
    this.reprocessando.set(notificacao.uuid);
    this.service
      .reprocessar(notificacao.uuid, notificacao.version, this.chaveUnica())
      .pipe(
        finalize(() => this.reprocessando.set('')),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.aviso.set('Notificação devolvida à fila; o próximo despacho tenta de novo.');
          this.carregar();
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível reprocessar a notificação.')),
      });
  }

  protected total(status: NotificacaoStatus): number {
    return this.fila()?.summary[status] ?? 0;
  }

  protected rotuloStatus(status: NotificacaoStatus): string {
    return {
      PENDENTE: 'Pendente',
      ENVIANDO: 'Em envio',
      ENVIADA: 'Enviada',
      FALHA: 'Falha',
      CANCELADA: 'Cancelada',
    }[status];
  }

  protected estadoStatus(status: NotificacaoStatus): string {
    return {
      PENDENTE: 'pending',
      ENVIANDO: 'review',
      ENVIADA: 'released',
      FALHA: 'blocked',
      CANCELADA: 'canceled',
    }[status];
  }

  protected rotuloEvento(event: NotificacaoEvento): string {
    return {
      TAREFA_A_VENCER: 'Tarefa a vencer',
      TAREFA_VENCE_EM_BREVE: 'Tarefa próxima do vencimento',
      TAREFA_VENCIDA: 'Tarefa vencida',
      TAREFA_VENCIDA_CRITICA: 'Atraso crítico',
      PROCESSO_PROXIMO_LIMITE: 'Processo próximo do limite',
      TAREFA_ATRIBUIDA: 'Tarefa atribuída',
      PENDENCIA_BLOQUEANTE: 'Pendência bloqueante',
      VALOR_AGUARDA_DECISAO: 'Valor aguardando decisão',
      VALOR_DECIDIDO: 'Valor decidido',
    }[event];
  }

  private chaveUnica(): string {
    return typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `reprocess-${Date.now()}-${Math.random()}`;
  }
}
