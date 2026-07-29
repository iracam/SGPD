import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { TagModule } from 'primeng/tag';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { ItemChecklist, TarefaSetor } from './models/tarefas.models';
import { TarefasService } from './tarefas.service';

@Component({
  selector: 'app-tarefas-page',
  imports: [DatePipe, ButtonModule, MessageModule, TagModule],
  templateUrl: './tarefas.html',
  styleUrl: './tarefas.scss',
})
export class TarefasPage {
  private readonly service = inject(TarefasService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly idempotencyKeys = new Map<string, string>();

  readonly tarefas = signal<TarefaSetor[]>([]);
  readonly carregando = signal(true);
  readonly tarefaEmMutacao = signal<number | null>(null);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly respostas = signal<Record<number, unknown>>({});
  readonly observacoes = signal<Record<number, string>>({});

  constructor() {
    this.carregar();
  }

  protected iniciar(tarefa: TarefaSetor): void {
    if (this.tarefaEmMutacao() !== null || tarefa.status !== 'PENDENTE') {
      return;
    }
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    this.service
      .iniciar(tarefa.id, tarefa.version, this.chave(`start:${tarefa.id}`))
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizada) => {
          this.substituir(atualizada);
          this.aviso.set(
            atualizada.idempotency_replayed
              ? 'O início anterior foi recuperado sem duplicação.'
              : 'Tarefa colocada em análise.',
          );
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível iniciar a tarefa.')),
      });
  }

  protected concluir(tarefa: TarefaSetor): void {
    if (this.tarefaEmMutacao() !== null || tarefa.status !== 'EM_ANALISE') {
      return;
    }
    const respostas = this.respostas();
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    this.service
      .concluir(
        tarefa.id,
        {
          expected_version: tarefa.version,
          answers: tarefa.checklist_items
            .filter((item) => Object.hasOwn(respostas, item.id))
            .map((item) => ({ item_id: item.id, value: respostas[item.id] })),
          notes: this.observacoes()[tarefa.id] ?? '',
        },
        this.chave(`complete:${tarefa.id}`),
      )
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizada) => {
          this.substituir(atualizada);
          this.aviso.set(
            atualizada.idempotency_replayed
              ? 'A conclusão anterior foi recuperada sem duplicação.'
              : 'Tarefa concluída e auditada.',
          );
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível concluir a tarefa.')),
      });
  }

  protected atualizarResposta(item: ItemChecklist, event: Event): void {
    const target = event.target;
    let value: unknown;
    if (target instanceof HTMLSelectElement && target.multiple) {
      value = Array.from(target.selectedOptions).map((option) => option.value);
    } else if (target instanceof HTMLInputElement && item.response_type === 'CONFIRMATION') {
      value = target.checked ? true : undefined;
    } else if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      value = target.value;
    } else if (target instanceof HTMLSelectElement) {
      value = target.value;
    }
    if (value === '') {
      value = undefined;
    } else if (item.response_type === 'BOOLEAN') {
      value = value === 'true';
    } else if (item.response_type === 'NUMBER' && typeof value === 'string') {
      value = Number(value);
    }
    this.respostas.update((current) => {
      const next = { ...current };
      if (value === undefined) {
        delete next[item.id];
      } else {
        next[item.id] = value;
      }
      return next;
    });
  }

  protected atualizarObservacao(taskId: number, event: Event): void {
    const value = event.target instanceof HTMLTextAreaElement ? event.target.value : '';
    this.observacoes.update((current) => ({ ...current, [taskId]: value }));
  }

  protected severidade(tarefa: TarefaSetor): 'warn' | 'info' | 'success' {
    if (tarefa.status === 'CONCLUIDA') {
      return 'success';
    }
    return tarefa.status === 'EM_ANALISE' ? 'info' : 'warn';
  }

  private carregar(): void {
    this.carregando.set(true);
    this.limparMensagens();
    this.service
      .listar()
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => this.tarefas.set(result.results),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar as tarefas.')),
      });
  }

  private substituir(atualizada: TarefaSetor): void {
    this.tarefas.update((tarefas) =>
      tarefas.map((tarefa) => (tarefa.id === atualizada.id ? atualizada : tarefa)),
    );
  }

  private limparMensagens(): void {
    this.erro.set('');
    this.aviso.set('');
  }

  private chave(action: string): string {
    const existing = this.idempotencyKeys.get(action);
    if (existing) {
      return existing;
    }
    const generated =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${action}-${Date.now()}`;
    this.idempotencyKeys.set(action, generated);
    return generated;
  }
}
