import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import {
  DecisaoValor,
  Evidencia,
  ItemChecklist,
  Pendencia,
  PendenciaStatus,
  PendenciaTransicao,
  TarefaSetor,
  TarefaStatus,
} from './models/tarefas.models';
import { TarefasService } from './tarefas.service';

interface ProcessoComTarefas {
  uuid: string;
  companyCode: number;
  branchCode: number;
  employeeName: string;
  employeeRegistration: number;
  dueDate: string;
  tarefas: TarefaSetor[];
}

interface RascunhoPendencia {
  title: string;
  description: string;
  category: string;
  blocking_level: string;
  checklist_item_id: number | null;
}

/** Um rascunho por pendência: cada ação do eixo de valor tem campo próprio. */
interface RascunhoValor {
  informed_amount: string;
  informed_justification: string;
  assessed_amount: string;
  assessed_justification: string;
  contested_amount: string;
  contested_justification: string;
  decision: DecisaoValor;
  approved_amount: string;
  opinion: string;
}

const RASCUNHO_VALOR_VAZIO: RascunhoValor = {
  informed_amount: '',
  informed_justification: '',
  assessed_amount: '',
  assessed_justification: '',
  contested_amount: '',
  contested_justification: '',
  decision: 'APROVADA_COBRANCA',
  approved_amount: '',
  opinion: '',
};

function agruparPorProcesso(
  tarefas: TarefaSetor[],
  concluido: boolean,
): ProcessoComTarefas[] {
  const ordenadas = [...tarefas].sort((left, right) => {
    const leftDate = concluido ? left.completed_at : left.due_at;
    const rightDate = concluido ? right.completed_at : right.due_at;
    const difference = new Date(rightDate ?? 0).getTime() - new Date(leftDate ?? 0).getTime();
    return concluido ? difference : -difference;
  });
  const processos = new Map<string, ProcessoComTarefas>();
  for (const tarefa of ordenadas) {
    const current = processos.get(tarefa.process.uuid);
    if (current) {
      current.tarefas.push(tarefa);
      continue;
    }
    processos.set(tarefa.process.uuid, {
      uuid: tarefa.process.uuid,
      companyCode: tarefa.process.company_code,
      branchCode: tarefa.process.branch_code,
      employeeName: tarefa.process.employee_name,
      employeeRegistration: tarefa.process.employee_registration,
      dueDate: tarefa.process.due_date,
      tarefas: [tarefa],
    });
  }
  return [...processos.values()];
}

@Component({
  selector: 'app-tarefas-page',
  imports: [DatePipe, ButtonModule, MessageModule],
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
  readonly rascunhosPendencia = signal<Record<number, RascunhoPendencia>>({});
  // Pendencia ainda sem rascunho de comentario nao tem chave no record: o tipo
  // precisa admitir undefined para o template nao renderizar a string literal.
  readonly comentariosPendencia = signal<Record<string, string | undefined>>({});
  readonly rascunhosValor = signal<Record<string, RascunhoValor | undefined>>({});
  readonly grupos = computed(() => {
    const tarefas = this.tarefas();
    return [
      {
        key: 'ativas',
        title: 'Ativas (a concluir)',
        description: 'Pendentes e em análise.',
        icon: 'pi pi-clock',
        emptyTitle: 'Nenhuma tarefa ativa',
        emptyText: 'Não há tarefas pendentes ou em análise para seus vínculos vigentes.',
        processos: agruparPorProcesso(
          tarefas.filter((tarefa) => tarefa.status !== 'CONCLUIDA'),
          false,
        ),
      },
      {
        key: 'concluidas',
        title: 'Concluídas',
        description: 'Da conclusão mais nova para a mais antiga.',
        icon: 'pi pi-check-circle',
        emptyTitle: 'Nenhuma tarefa concluída',
        emptyText: 'As tarefas concluídas aparecerão aqui, com as mais novas no topo.',
        processos: agruparPorProcesso(
          tarefas.filter((tarefa) => tarefa.status === 'CONCLUIDA'),
          true,
        ),
      },
    ];
  });

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

  protected criarPendencia(tarefa: TarefaSetor): void {
    if (this.tarefaEmMutacao() !== null || tarefa.status !== 'EM_ANALISE') {
      return;
    }
    const draft = this.rascunhosPendencia()[tarefa.id] ?? this.novoRascunhoPendencia();
    if (!draft.title.trim() || !draft.description.trim()) {
      this.erro.set('Informe o título e a descrição da pendência.');
      return;
    }
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    this.service
      .criarPendencia(
        {
          task_id: tarefa.id,
          expected_task_version: tarefa.version,
          checklist_item_id: draft.checklist_item_id,
          category: draft.category,
          title: draft.title,
          description: draft.description,
          blocking_level: draft.blocking_level,
          items: [],
        },
        this.chaveUnica('pending'),
      )
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (pendencia) => {
          this.tarefas.update((tarefas) =>
            tarefas.map((row) =>
              row.id === tarefa.id
                ? { ...row, pending_items: [pendencia, ...row.pending_items] }
                : row,
            ),
          );
          this.rascunhosPendencia.update((current) => ({
            ...current,
            [tarefa.id]: this.novoRascunhoPendencia(),
          }));
          this.aviso.set(
            pendencia.idempotency_replayed
              ? 'A pendência anterior foi recuperada sem duplicação.'
              : 'Pendência registrada e auditada.',
          );
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível registrar a pendência.')),
      });
  }

  protected atualizarCampoPendencia(
    taskId: number,
    field: keyof RascunhoPendencia,
    event: Event,
  ): void {
    const target = event.target;
    const raw =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement
        ? target.value
        : '';
    const value = field === 'checklist_item_id' ? (raw ? Number(raw) : null) : raw;
    this.rascunhosPendencia.update((current) => ({
      ...current,
      [taskId]: {
        ...(current[taskId] ?? this.novoRascunhoPendencia()),
        [field]: value,
      },
    }));
  }

  protected atualizarComentarioPendencia(pendingUuid: string, event: Event): void {
    const value = event.target instanceof HTMLTextAreaElement ? event.target.value : '';
    this.comentariosPendencia.update((current) => ({
      ...current,
      [pendingUuid]: value,
    }));
  }

  protected comentarPendencia(tarefa: TarefaSetor, pendencia: Pendencia): void {
    const comment = (this.comentariosPendencia()[pendencia.uuid] ?? '').trim();
    if (!comment) {
      this.erro.set('Informe o comentário da pendência.');
      return;
    }
    this.mutarPendencia(
      tarefa,
      pendencia,
      this.service.comentarPendencia(
        pendencia.uuid,
        pendencia.version,
        comment,
        this.chaveUnica('pending-comment'),
      ),
      'Comentário registrado e auditado.',
    );
  }

  protected transicionarPendencia(
    tarefa: TarefaSetor,
    pendencia: Pendencia,
    status: PendenciaStatus,
  ): void {
    const comment = (this.comentariosPendencia()[pendencia.uuid] ?? '').trim();
    if (!comment) {
      this.erro.set('Informe um comentário para justificar a transição.');
      return;
    }
    this.mutarPendencia(
      tarefa,
      pendencia,
      this.service.alterarPendencia(
        pendencia.uuid,
        pendencia.version,
        status,
        comment,
        this.chaveUnica('pending-status'),
      ),
      'Situação da pendência atualizada.',
    );
  }

  /** Rascunho do valor sempre definido, para o template nunca ligar a `undefined`. */
  protected valor(pendencia: Pendencia): RascunhoValor {
    return this.rascunhosValor()[pendencia.uuid] ?? RASCUNHO_VALOR_VAZIO;
  }

  protected atualizarValor(
    pendingUuid: string,
    field: keyof RascunhoValor,
    event: Event,
  ): void {
    const target = event.target;
    const value =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement
        ? target.value
        : '';
    this.rascunhosValor.update((current) => ({
      ...current,
      [pendingUuid]: {
        ...(current[pendingUuid] ?? RASCUNHO_VALOR_VAZIO),
        [field]: value,
      },
    }));
  }

  /** Lançar pretensão exige pendência de valor aberta em setor habilitado. */
  protected podeInformarValor(tarefa: TarefaSetor, pendencia: Pendencia): boolean {
    return (
      pendencia.category === 'VALOR' &&
      pendencia.amount === null &&
      pendencia.status === 'ABERTA' &&
      tarefa.sector.allows_amount
    );
  }

  protected valorEmAnalise(pendencia: Pendencia): boolean {
    return pendencia.status === 'ENCAMINHADA_ANALISE' || pendencia.status === 'CONTESTADA';
  }

  /** Apurar e decidir são do DP no escopo; contestar é de quem responde pelo setor. */
  protected podeAnalisarValor(pendencia: Pendencia): boolean {
    return pendencia.can_analyse_amount && this.valorEmAnalise(pendencia);
  }

  protected podeContestarValor(pendencia: Pendencia): boolean {
    return pendencia.status === 'ENCAMINHADA_ANALISE';
  }

  protected informarValor(tarefa: TarefaSetor, pendencia: Pendencia): void {
    const draft = this.valor(pendencia);
    if (!draft.informed_amount.trim() || !draft.informed_justification.trim()) {
      this.erro.set('Informe o valor pretendido e a justificativa.');
      return;
    }
    this.mutarPendencia(
      tarefa,
      pendencia,
      this.service.informarValor(
        pendencia.uuid,
        pendencia.version,
        {
          amount_informed: draft.informed_amount.trim(),
          justification: draft.informed_justification.trim(),
        },
        this.chaveUnica('amount'),
      ),
      'Pretensão de cobrança registrada para análise.',
    );
  }

  protected apurarValor(tarefa: TarefaSetor, pendencia: Pendencia): void {
    const draft = this.valor(pendencia);
    if (!draft.assessed_amount.trim() || !draft.assessed_justification.trim()) {
      this.erro.set('Informe o valor apurado e a justificativa.');
      return;
    }
    this.mutarPendencia(
      tarefa,
      pendencia,
      this.service.apurarValor(
        pendencia.uuid,
        pendencia.version,
        {
          amount_assessed: draft.assessed_amount.trim(),
          justification: draft.assessed_justification.trim(),
        },
        this.chaveUnica('amount-assess'),
      ),
      'Valor apurado registrado; a pretensão segue aguardando decisão.',
    );
  }

  protected contestarValor(tarefa: TarefaSetor, pendencia: Pendencia): void {
    const draft = this.valor(pendencia);
    if (!draft.contested_amount.trim() || !draft.contested_justification.trim()) {
      this.erro.set('Informe o valor contestado e a justificativa.');
      return;
    }
    this.mutarPendencia(
      tarefa,
      pendencia,
      this.service.contestarValor(
        pendencia.uuid,
        pendencia.version,
        {
          amount_contested: draft.contested_amount.trim(),
          justification: draft.contested_justification.trim(),
        },
        this.chaveUnica('amount-contest'),
      ),
      'Contestação registrada na pretensão.',
    );
  }

  protected decidirValor(tarefa: TarefaSetor, pendencia: Pendencia): void {
    const draft = this.valor(pendencia);
    const aprovaCobranca = draft.decision === 'APROVADA_COBRANCA';
    if (!draft.opinion.trim()) {
      this.erro.set('Informe o parecer da decisão.');
      return;
    }
    if (aprovaCobranca && !draft.approved_amount.trim()) {
      this.erro.set('A aprovação de cobrança exige o valor aprovado.');
      return;
    }
    this.mutarPendencia(
      tarefa,
      pendencia,
      this.service.decidirValor(
        pendencia.uuid,
        pendencia.version,
        {
          decision: draft.decision,
          opinion: draft.opinion.trim(),
          // Rejeição e abono resolvem em zero no service: enviar valor é erro de contrato.
          ...(aprovaCobranca ? { amount_approved: draft.approved_amount.trim() } : {}),
        },
        this.chaveUnica('amount-decide'),
      ),
      'Decisão registrada na trilha da pretensão.',
    );
  }

  protected rotuloDecisao(decision: DecisaoValor): string {
    return {
      APROVADA_COBRANCA: 'Aprovada para cobrança',
      REJEITADA: 'Rejeitada',
      ABONADA: 'Abonada',
    }[decision];
  }

  /** Valor legível em pt-BR; o dado bruto continua sendo o string do backend. */
  protected valorFormatado(value: string | null, currency: string): string {
    if (value === null) {
      return '—';
    }
    return `${currency} ${Number(value).toLocaleString('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  protected enviarEvidencia(
    tarefa: TarefaSetor,
    event: Event,
    item?: ItemChecklist,
    pendencia?: Pendencia,
  ): void {
    const input = event.target instanceof HTMLInputElement ? event.target : null;
    const file = input?.files?.[0];
    if (!file || this.tarefaEmMutacao() !== null || tarefa.status !== 'EM_ANALISE') {
      return;
    }
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    this.service
      .enviarEvidencia(
        tarefa.id,
        tarefa.version,
        file,
        this.chaveUnica('evidence'),
        item?.id,
        pendencia?.uuid,
      )
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (evidence) => {
          this.adicionarEvidencia(tarefa.id, evidence);
          if (input) {
            input.value = '';
          }
          this.aviso.set(
            evidence.idempotency_replayed
              ? 'O envio anterior foi recuperado sem duplicação.'
              : 'Evidência privada enviada e auditada.',
          );
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível enviar a evidência.')),
      });
  }

  protected transicoesDisponiveis(status: PendenciaStatus): PendenciaTransicao[] {
    if (status === 'ABERTA') {
      return ['EM_REGULARIZACAO'];
    }
    if (status === 'EM_REGULARIZACAO') {
      return ['REGULARIZADA'];
    }
    if (status === 'REGULARIZADA') {
      return ['EM_REGULARIZACAO', 'ENCERRADA'];
    }
    return [];
  }

  protected rotuloTransicao(status: PendenciaTransicao): string {
    return {
      ABERTA: 'Reabrir',
      EM_REGULARIZACAO: 'Iniciar regularização',
      REGULARIZADA: 'Marcar regularizada',
      ENCERRADA: 'Encerrar',
    }[status];
  }

  protected tamanhoEvidencia(value: number): string {
    return value < 1024 * 1024
      ? `${Math.ceil(value / 1024)} KiB`
      : `${(value / (1024 * 1024)).toFixed(1)} MiB`;
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

  /** Item já conferido: respondido nesta sessão ou registrado na conclusão. */
  protected conferido(item: ItemChecklist): boolean {
    return item.answered_at !== null || Object.hasOwn(this.respostas(), item.id);
  }

  protected rotuloStatus(status: TarefaStatus): string {
    return { PENDENTE: 'Pendente', EM_ANALISE: 'Em análise', CONCLUIDA: 'Concluída' }[
      status
    ];
  }

  /** Modificador do chip: reutiliza os tokens --status-* da identidade. */
  protected estadoTarefa(status: TarefaStatus): string {
    return { PENDENTE: 'pending', EM_ANALISE: 'review', CONCLUIDA: 'released' }[status];
  }

  protected rotuloStatusPendencia(status: PendenciaStatus): string {
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

  protected estadoPendencia(status: PendenciaStatus): string {
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

  protected rotuloCategoria(category: string): string {
    return (
      {
        MATERIAL: 'Material',
        FERRAMENTA: 'Ferramenta',
        EQUIPAMENTO: 'Equipamento',
        DOCUMENTO: 'Documento',
        ACESSO: 'Acesso',
        EXAME: 'Exame',
        ATIVIDADE: 'Atividade',
        VEICULO: 'Veículo',
        PATRIMONIO: 'Patrimônio',
        CONTRATO: 'Contrato',
        OUTRO: 'Outro',
      }[category] ?? category
    );
  }

  protected rotuloBloqueio(level: Pendencia['blocking_level']): string {
    return {
      BLOQUEANTE: 'Bloqueante',
      BLOQUEANTE_ATE_DECISAO: 'Bloqueante até decisão',
      NAO_BLOQUEANTE: 'Não bloqueante',
      INFORMATIVA: 'Informativa',
    }[level];
  }

  /** Resposta registrada, legível, para o histórico da tarefa concluída. */
  protected respostaRegistrada(item: ItemChecklist): string {
    const value = item.response;
    if (value === null || value === undefined || value === '') {
      return 'Sem resposta';
    }
    if (item.response_type === 'CONFIRMATION') {
      return 'Confirmado';
    }
    if (item.response_type === 'BOOLEAN') {
      return value ? 'Sim' : 'Não';
    }
    if (item.response_type === 'DATE' && typeof value === 'string') {
      return value.split('-').reverse().join('/');
    }
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return String(value);
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

  private mutarPendencia(
    tarefa: TarefaSetor,
    pendencia: Pendencia,
    request: ReturnType<TarefasService['comentarPendencia']>,
    successMessage: string,
  ): void {
    if (this.tarefaEmMutacao() !== null) {
      return;
    }
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    request
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (updated) => {
          this.tarefas.update((tarefas) =>
            tarefas.map((row) =>
              row.id === tarefa.id
                ? {
                    ...row,
                    pending_items: row.pending_items.map((current) =>
                      current.uuid === pendencia.uuid ? updated : current,
                    ),
                  }
                : row,
            ),
          );
          this.comentariosPendencia.update((current) => ({
            ...current,
            [pendencia.uuid]: '',
          }));
          this.rascunhosValor.update((current) => ({
            ...current,
            [pendencia.uuid]: RASCUNHO_VALOR_VAZIO,
          }));
          this.aviso.set(successMessage);
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível alterar a pendência.')),
      });
  }

  private adicionarEvidencia(taskId: number, evidence: Evidencia): void {
    this.tarefas.update((tarefas) =>
      tarefas.map((task) => {
        if (task.id !== taskId) {
          return task;
        }
        return {
          ...task,
          evidences: [evidence, ...task.evidences],
          checklist_items: task.checklist_items.map((item) =>
            item.id === evidence.checklist_item_id
              ? { ...item, evidences: [evidence, ...item.evidences] }
              : item,
          ),
        };
      }),
    );
  }

  private novoRascunhoPendencia(): RascunhoPendencia {
    return {
      title: '',
      description: '',
      category: 'OUTRO',
      blocking_level: 'BLOQUEANTE',
      checklist_item_id: null,
    };
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

  private chaveUnica(action: string): string {
    return typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${action}-${Date.now()}-${Math.random()}`;
  }
}
