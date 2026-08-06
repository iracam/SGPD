import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { Observable, finalize } from 'rxjs';

import { errorMessage, fieldErrors } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import {
  ConferenciaEncerramento,
  EstadoFormal,
  PreviaExclusao,
  SituacaoProcesso,
  TarefaDoCiclo,
} from './models/processo-encerramento.models';
import { ProcessoEncerramentoService } from './processo-encerramento.service';

/**
 * Conferência e atos formais do ciclo (RF-029 a RF-032, ADR-051).
 *
 * A tela separa o que foi decidido — o estado formal — do que está calculado —
 * a situação funcional e os impedimentos. Nenhum botão libera coisa alguma por
 * conta própria: o servidor refaz a prontidão sob lock e pode recusar o que
 * esta página mostrava como pronto.
 */
@Component({
  selector: 'app-processo-encerramento-page',
  imports: [DatePipe, RouterLink, ButtonModule, MessageModule],
  templateUrl: './processo-encerramento.html',
  styleUrl: './processo-encerramento.scss',
})
export class ProcessoEncerramentoPage {
  private readonly service = inject(ProcessoEncerramentoService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly uuid = this.route.snapshot.paramMap.get('uuid') ?? '';

  readonly dados = signal<ConferenciaEncerramento | null>(null);
  readonly carregando = signal(true);
  readonly enviando = signal(false);
  readonly erro = signal('');
  readonly aviso = signal('');

  readonly observacao = signal('');
  readonly motivo = signal('');
  readonly numeroRescisao = signal('');
  readonly dataProcessamento = signal(this.hoje());
  readonly tarefasSelecionadas = signal<number[]>([]);
  readonly justificativaOverride = signal('');

  /** Exclusão definitiva: a prévia só é buscada quando alguém pede (ADR-056). */
  readonly previaExclusao = signal<PreviaExclusao | null>(null);
  readonly conferindoExclusao = signal(false);
  /** Justificativa própria: cancelar e excluir convivem na mesma tela e não
   * podem dividir o mesmo campo — são atos diferentes, com efeitos diferentes. */
  readonly motivoExclusao = signal('');

  /** A reabertura é exclusiva do SuperAdmin; a API repete a decisão. */
  readonly podeReabrir = computed(() => this.auth.currentUser()?.is_superuser === true);

  /**
   * A SPA só oferece o override a quem `can_override_blockers` autoriza; a
   * decisão em si é sempre revalidada pelo service sob lock (ADR-054).
   */
  readonly podeLiberarComOverride = computed(
    () => !this.dados()?.readiness.is_ready && this.dados()?.can_override_blockers === true,
  );
  readonly podeEncerrarComOverride = computed(
    () =>
      (this.dados()?.closing_blockers.length ?? 0) > 0 &&
      this.dados()?.can_override_blockers === true,
  );

  readonly tarefasConcluidas = computed(() =>
    (this.dados()?.tasks ?? []).filter((tarefa) => tarefa.status === 'CONCLUIDA'),
  );

  /**
   * Cancelar o processo já formalizado é ato da gerência (ADR-056). O `DP` puro
   * continua cancelando rascunho e iniciado; a decisão é refeita no servidor.
   */
  readonly podeCancelarFormalizado = computed(() => {
    const status = this.dados()?.process.status;
    return (
      this.dados()?.can_override_blockers === true &&
      (status === 'LIBERADO_PARA_RESCISAO' ||
        status === 'RESCISAO_PROCESSADA' ||
        status === 'ENCERRADO')
    );
  });

  /** Processo encerrado nunca é excluído — para ele, o caminho é cancelar. */
  readonly podeTentarExcluir = computed(() => {
    const status = this.dados()?.process.status;
    return status !== undefined && status !== 'ENCERRADO';
  });

  /** Quantas linhas a exclusão destrói, só as que existem, para o aviso. */
  readonly resumoDaExclusao = computed(() => {
    const contagem = this.previaExclusao()?.counts;
    if (!contagem) {
      return [];
    }
    return [
      { rotulo: 'tarefas', valor: contagem.tasks },
      { rotulo: 'tarefas concluídas', valor: contagem.completed_tasks },
      { rotulo: 'pendências', valor: contagem.pending_items },
      { rotulo: 'valores informados', valor: contagem.pending_amounts },
      { rotulo: 'evidências', valor: contagem.evidences },
      { rotulo: 'notificações', valor: contagem.notifications },
      { rotulo: 'eventos de trilha', valor: contagem.audit_events },
    ].filter((linha) => linha.valor > 0);
  });

  constructor() {
    this.service
      .carregar(this.uuid)
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => this.dados.set(result),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar a conferência.')),
      });
  }

  protected liberar(): void {
    const processo = this.dados()?.process;
    if (!processo) {
      return;
    }
    this.executar(
      this.service.liberar(
        this.uuid,
        this.comOverride({ expected_version: processo.version, notes: this.observacao() }),
        this.chave(),
      ),
      'Processo liberado para rescisão.',
    );
  }

  protected registrarProcessamento(): void {
    const processo = this.dados()?.process;
    if (!processo) {
      return;
    }
    this.executar(
      this.service.registrarProcessamento(
        this.uuid,
        {
          expected_version: processo.version,
          termination_reference: this.numeroRescisao(),
          processed_on: this.dataProcessamento(),
          notes: this.observacao(),
        },
        this.chave(),
      ),
      'Processamento da rescisão registrado.',
    );
  }

  protected encerrar(): void {
    const processo = this.dados()?.process;
    if (!processo) {
      return;
    }
    this.executar(
      this.service.encerrar(
        this.uuid,
        this.comOverride({ expected_version: processo.version, notes: this.observacao() }),
        this.chave(),
      ),
      'Processo encerrado.',
    );
  }

  protected cancelar(): void {
    const processo = this.dados()?.process;
    if (!processo) {
      return;
    }
    this.executar(
      this.service.cancelar(
        this.uuid,
        { expected_version: processo.version, reason: this.motivo() },
        this.chave(),
      ),
      'Processo cancelado. As tarefas abertas foram encerradas.',
    );
  }

  protected reabrir(): void {
    const processo = this.dados()?.process;
    if (!processo) {
      return;
    }
    this.executar(
      this.service.reabrir(
        this.uuid,
        {
          expected_version: processo.version,
          reason: this.motivo(),
          task_ids: this.tarefasSelecionadas(),
        },
        this.chave(),
      ),
      'Processo reaberto.',
    );
  }

  /**
   * Primeiro passo da exclusão: buscar e mostrar o que será destruído.
   *
   * O aviso não é decorativo. Quem apaga um processo com tarefa concluída,
   * pendência ou evidência precisa ver o tamanho do que está descartando antes
   * de confirmar — depois não há de onde recuperar.
   */
  protected conferirExclusao(): void {
    this.erro.set('');
    this.aviso.set('');
    this.conferindoExclusao.set(true);
    this.service
      .previaExclusao(this.uuid)
      .pipe(
        finalize(() => this.conferindoExclusao.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (previa) => this.previaExclusao.set(previa),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível conferir a exclusão.')),
      });
  }

  protected desistirDaExclusao(): void {
    this.previaExclusao.set(null);
    this.motivoExclusao.set('');
  }

  protected excluir(): void {
    const processo = this.dados()?.process;
    if (!processo) {
      return;
    }
    this.erro.set('');
    this.aviso.set('');
    this.enviando.set(true);
    this.service
      .excluir(
        this.uuid,
        { expected_version: processo.version, reason: this.motivoExclusao() },
        this.chave(),
      )
      .pipe(
        finalize(() => this.enviando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        // O processo deixou de existir: não há o que recarregar nesta rota.
        next: () => void this.router.navigate(['/fe/processos']),
        error: (error) => this.erro.set(this.recusa(error)),
      });
  }

  protected alternarTarefa(tarefa: TarefaDoCiclo): void {
    this.tarefasSelecionadas.update((atual) =>
      atual.includes(tarefa.id)
        ? atual.filter((id) => id !== tarefa.id)
        : [...atual, tarefa.id],
    );
  }

  protected tarefaSelecionada(tarefa: TarefaDoCiclo): boolean {
    return this.tarefasSelecionadas().includes(tarefa.id);
  }

  protected texto(
    destino:
      | 'observacao'
      | 'motivo'
      | 'motivoExclusao'
      | 'numeroRescisao'
      | 'justificativaOverride',
    event: Event,
  ): void {
    const valor = (event.target as HTMLInputElement | HTMLTextAreaElement).value;
    this[destino].set(valor);
  }

  /** `override_reason` só entra no corpo quando há justificativa preenchida —
   * o campo é opcional no serializer e não faz sentido fora do override. */
  private comOverride<T extends { expected_version: number; notes: string }>(
    payload: T,
  ): T & { override_reason?: string } {
    const justificativa = this.justificativaOverride().trim();
    return justificativa ? { ...payload, override_reason: justificativa } : payload;
  }

  protected data(event: Event): void {
    this.dataProcessamento.set((event.target as HTMLInputElement).value);
  }

  protected rotuloEstado(status: EstadoFormal): string {
    return {
      RASCUNHO: 'Rascunho',
      INICIADO: 'Iniciado',
      LIBERADO_PARA_RESCISAO: 'Liberado para rescisão',
      RESCISAO_PROCESSADA: 'Rescisão processada',
      ENCERRADO: 'Encerrado',
      CANCELADO: 'Cancelado',
    }[status];
  }

  protected estadoDoChip(status: EstadoFormal): string {
    return {
      RASCUNHO: 'pending',
      INICIADO: 'review',
      LIBERADO_PARA_RESCISAO: 'released',
      RESCISAO_PROCESSADA: 'released',
      ENCERRADO: 'released',
      CANCELADO: 'canceled',
    }[status];
  }

  protected rotuloSituacao(situation: SituacaoProcesso): string {
    return {
      RASCUNHO: 'Rascunho',
      EM_VALIDACAO: 'Em validação',
      COM_PENDENCIAS: 'Com pendências',
      AGUARDANDO_REGULARIZACAO: 'Aguardando regularização',
      AGUARDANDO_DECISAO: 'Aguardando decisão',
      PRONTO_PARA_ANALISE_DP: 'Pronto para análise do DP',
      LIBERADO_PARA_RESCISAO: 'Liberado para rescisão',
      RESCISAO_PROCESSADA: 'Rescisão processada',
      ENCERRADO: 'Encerrado',
      CANCELADO: 'Cancelado',
    }[situation];
  }

  protected situacaoDoChip(situation: SituacaoProcesso): string {
    return {
      RASCUNHO: 'pending',
      EM_VALIDACAO: 'review',
      COM_PENDENCIAS: 'blocked',
      AGUARDANDO_REGULARIZACAO: 'pending',
      AGUARDANDO_DECISAO: 'blocked',
      PRONTO_PARA_ANALISE_DP: 'released',
      LIBERADO_PARA_RESCISAO: 'released',
      RESCISAO_PROCESSADA: 'released',
      ENCERRADO: 'released',
      CANCELADO: 'canceled',
    }[situation];
  }

  private executar(
    requisicao: Observable<ConferenciaEncerramento>,
    sucesso: string,
  ): void {
    this.erro.set('');
    this.aviso.set('');
    this.enviando.set(true);
    requisicao
      .pipe(
        finalize(() => this.enviando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => {
          this.dados.set(result);
          this.observacao.set('');
          this.motivo.set('');
          this.numeroRescisao.set('');
          this.tarefasSelecionadas.set([]);
          this.justificativaOverride.set('');
          this.aviso.set(
            result.idempotency_replayed ? 'O ato já havia sido registrado.' : sucesso,
          );
        },
        error: (error) => this.erro.set(this.recusa(error)),
      });
  }

  /**
   * A recusa do ato é a informação útil, não o rótulo genérico do envelope: o
   * impedimento que o servidor recalculou vem em `details` e precisa ser lido.
   */
  private recusa(error: unknown): string {
    const mensagens = Object.values(fieldErrors(error)).flat();
    return mensagens.length
      ? mensagens.join(' ')
      : errorMessage(error, 'Não foi possível concluir o ato.');
  }

  private hoje(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private chave(): string {
    return typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `encerramento-${this.uuid}-${Date.now()}`;
  }
}
