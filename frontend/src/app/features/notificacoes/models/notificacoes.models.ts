export type NotificacaoStatus =
  | 'PENDENTE'
  | 'ENVIANDO'
  | 'ENVIADA'
  | 'FALHA'
  | 'CANCELADA';

export type NotificacaoEvento =
  | 'TAREFA_A_VENCER'
  | 'TAREFA_VENCE_EM_BREVE'
  | 'TAREFA_VENCIDA'
  | 'TAREFA_VENCIDA_CRITICA'
  | 'PROCESSO_PROXIMO_LIMITE'
  | 'TAREFA_ATRIBUIDA'
  | 'PENDENCIA_BLOQUEANTE'
  | 'VALOR_AGUARDA_DECISAO'
  | 'VALOR_DECIDIDO';

export interface TentativaEntrega {
  readonly attempt_number: number;
  readonly started_at: string;
  readonly finished_at: string | null;
  readonly succeeded: boolean | null;
  readonly error: string;
}

export interface Notificacao {
  readonly uuid: string;
  readonly event: NotificacaoEvento;
  readonly channel: string;
  readonly status: NotificacaoStatus;
  readonly subject: string;
  readonly body: string;
  readonly process_uuid: string;
  readonly process_ref: string;
  readonly task_id: number | null;
  readonly sector_name: string | null;
  readonly recipient: { readonly id: number; readonly username: string; readonly email: string };
  readonly attempts: number;
  readonly max_attempts: number;
  readonly next_attempt_at: string;
  readonly sent_at: string | null;
  readonly last_error: string;
  readonly created_at: string;
  readonly version: number;
  readonly delivery_attempts: readonly TentativaEntrega[];
}

export interface FilaNotificacoes {
  readonly results: readonly Notificacao[];
  /** Contagem por situação da fila inteira do escopo, antes dos filtros. */
  readonly summary: Partial<Record<NotificacaoStatus, number>>;
}
