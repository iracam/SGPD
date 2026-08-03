import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { finalize, forkJoin } from 'rxjs';

import { AjudaLink } from '../../core/ajuda/ajuda-link';
import { errorMessage } from '../../core/api/api-error';
import { ProcessoResumo, TarefaProcesso } from './models/processos.models';
import { ProcessosService } from './processos.service';

@Component({
  selector: 'app-processos-page',
  imports: [DatePipe, RouterLink, ButtonModule, MessageModule, AjudaLink],
  templateUrl: './processos.html',
  styleUrl: './processos.scss',
})
export class ProcessosPage {
  private readonly service = inject(ProcessosService);
  private readonly destroyRef = inject(DestroyRef);

  readonly rascunhos = signal<ProcessoResumo[]>([]);
  readonly emAberto = signal<ProcessoResumo[]>([]);
  readonly concluidos = signal<ProcessoResumo[]>([]);
  readonly cancelados = signal<ProcessoResumo[]>([]);
  readonly carregando = signal(true);
  readonly processoExpandido = signal<string | null>(null);
  readonly carregandoTarefas = signal<string | null>(null);
  readonly tarefasPorProcesso = signal<
    Partial<Record<string, TarefaProcesso[]>>
  >({});
  readonly erro = signal('');
  readonly cardsExpansiveis = computed(() => [
    {
      key: 'open',
      title: 'Em Aberto',
      description: 'Iniciados com tarefas a concluir.',
      icon: 'pi pi-clock',
      loadingText: 'Carregando processos em aberto…',
      emptyText: 'Nenhum processo em aberto disponível.',
      taskLoadingText: 'Carregando tarefas do processo…',
      taskEmptyText: 'Nenhuma tarefa registrada para este processo.',
      completedOnly: false,
      processes: this.emAberto(),
    },
    {
      key: 'completed',
      title: 'Concluídos',
      description: 'Encerrados ou com todas as tarefas concluídas.',
      icon: 'pi pi-check-circle',
      loadingText: 'Carregando processos concluídos…',
      emptyText: 'Nenhum processo concluído disponível.',
      taskLoadingText: 'Carregando tarefas concluídas…',
      taskEmptyText: 'Nenhuma tarefa concluída registrada para este processo.',
      completedOnly: true,
      processes: this.concluidos(),
    },
    {
      key: 'cancelled',
      title: 'Cancelados',
      description: 'Cancelados com justificativa; o histórico permanece.',
      icon: 'pi pi-ban',
      loadingText: 'Carregando processos cancelados…',
      emptyText: 'Nenhum processo cancelado.',
      taskLoadingText: 'Carregando tarefas do processo…',
      taskEmptyText: 'Nenhuma tarefa registrada para este processo.',
      completedOnly: false,
      processes: this.cancelados(),
    },
  ]);

  constructor() {
    forkJoin({
      rascunhos: this.service.listarRascunhos(),
      emAberto: this.service.listarEmAberto(),
      concluidos: this.service.listarConcluidos(),
      cancelados: this.service.listarCancelados(),
    })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (response) => {
          this.rascunhos.set(response.rascunhos.results);
          this.emAberto.set(response.emAberto.results);
          this.concluidos.set(response.concluidos.results);
          this.cancelados.set(response.cancelados.results);
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar os processos.')),
      });
  }

  protected alternarTarefas(
    processo: ProcessoResumo,
    apenasConcluidas: boolean,
  ): void {
    if (this.processoExpandido() === processo.uuid) {
      this.processoExpandido.set(null);
      return;
    }
    this.processoExpandido.set(processo.uuid);
    if (Object.hasOwn(this.tarefasPorProcesso(), processo.uuid)) {
      return;
    }
    this.erro.set('');
    this.carregandoTarefas.set(processo.uuid);
    this.service
      .listarTarefas(processo.uuid, apenasConcluidas)
      .pipe(
        finalize(() => this.carregandoTarefas.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (response) =>
          this.tarefasPorProcesso.update((current) => ({
            ...current,
            [processo.uuid]: response.results,
          })),
        error: (error) => {
          this.processoExpandido.set(null);
          this.erro.set(
            errorMessage(error, 'Não foi possível carregar as tarefas do processo.'),
          );
        },
      });
  }

  protected rotuloStatusTarefa(status: TarefaProcesso['status']): string {
    return {
      PENDENTE: 'Pendente',
      EM_ANALISE: 'Em análise',
      CONCLUIDA: 'Concluída',
      CANCELADA: 'Cancelada',
    }[status];
  }

  /** Modificador do chip: reutiliza os tokens --status-* da identidade. */
  protected estadoTarefa(status: TarefaProcesso['status']): string {
    return {
      PENDENTE: 'pending',
      EM_ANALISE: 'review',
      CONCLUIDA: 'released',
      CANCELADA: 'canceled',
    }[status];
  }
}
