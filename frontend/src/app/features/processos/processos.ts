import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MessageModule } from 'primeng/message';
import { finalize, forkJoin } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { ProcessoResumo, TarefaConcluidaProcesso } from './models/processos.models';
import { ProcessosService } from './processos.service';

@Component({
  selector: 'app-processos-page',
  imports: [DatePipe, RouterLink, MessageModule],
  templateUrl: './processos.html',
  styleUrl: './processos.scss',
})
export class ProcessosPage {
  private readonly service = inject(ProcessosService);
  private readonly destroyRef = inject(DestroyRef);

  readonly rascunhos = signal<ProcessoResumo[]>([]);
  readonly concluidos = signal<ProcessoResumo[]>([]);
  readonly carregando = signal(true);
  readonly processoExpandido = signal<string | null>(null);
  readonly carregandoTarefas = signal<string | null>(null);
  readonly tarefasPorProcesso = signal<
    Partial<Record<string, TarefaConcluidaProcesso[]>>
  >({});
  readonly erro = signal('');

  constructor() {
    forkJoin({
      rascunhos: this.service.listarRascunhos(),
      concluidos: this.service.listarConcluidos(),
    })
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (response) => {
          this.rascunhos.set(response.rascunhos.results);
          this.concluidos.set(response.concluidos.results);
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar os processos.')),
      });
  }

  protected alternarTarefas(processo: ProcessoResumo): void {
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
      .listarTarefasConcluidas(processo.uuid)
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
}
