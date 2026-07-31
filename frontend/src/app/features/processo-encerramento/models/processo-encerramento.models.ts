/** Estado formal do processo: o que foi decidido, e só isso (ADR-051). */
export type EstadoFormal =
  | 'RASCUNHO'
  | 'INICIADO'
  | 'LIBERADO_PARA_RESCISAO'
  | 'RESCISAO_PROCESSADA'
  | 'ENCERRADO'
  | 'CANCELADO';

/** Situação funcional: onde o trabalho está. Calculada a cada leitura, nunca gravada. */
export type SituacaoProcesso =
  | 'RASCUNHO'
  | 'EM_VALIDACAO'
  | 'COM_PENDENCIAS'
  | 'AGUARDANDO_REGULARIZACAO'
  | 'AGUARDANDO_DECISAO'
  | 'PRONTO_PARA_ANALISE_DP'
  | 'LIBERADO_PARA_RESCISAO'
  | 'RESCISAO_PROCESSADA'
  | 'ENCERRADO'
  | 'CANCELADO';

export interface AtorRegistrado {
  id: number;
  username: string;
}

export interface MarcasFormais {
  released_at: string | null;
  released_by: AtorRegistrado | null;
  release_notes: string;
  /** Declaração do DP sobre o Senior, não leitura dele (ADR-051). */
  termination_reference: string;
  termination_processed_on: string | null;
  processing_registered_at: string | null;
  processing_registered_by: AtorRegistrado | null;
  processing_notes: string;
  closed_at: string | null;
  closed_by: AtorRegistrado | null;
  closing_notes: string;
  cancelled_at: string | null;
  cancelled_by: AtorRegistrado | null;
  cancellation_reason: string;
}

export interface Prontidao {
  situation: SituacaoProcesso;
  is_ready: boolean;
  blockers: string[];
  warnings: string[];
  task_count: number;
  required_task_count: number;
  completed_task_count: number;
  open_task_count: number;
  blocking_pending_count: number;
  open_pending_count: number;
  undecided_amount_count: number;
}

export interface ProcessoFormal {
  uuid: string;
  status: EstadoFormal;
  company_code: number;
  branch_code: number;
  employee_registration: number;
  planned_termination_date: string;
  due_date: string;
  version: number;
  formal: MarcasFormais;
  employee_snapshot: {
    employee_name: string;
    registration: number;
    branch_legal_name: string;
  };
}

export interface TarefaDoCiclo {
  id: number;
  status: 'PENDENTE' | 'EM_ANALISE' | 'CONCLUIDA' | 'CANCELADA';
  sector: { id: number; code: string; name: string };
  due_at: string;
  completed_at: string | null;
}

export interface ConferenciaEncerramento {
  process: ProcessoFormal;
  readiness: Prontidao;
  /** Pendência ainda em curso impede o encerramento, não a liberação. */
  closing_blockers: string[];
  tasks: TarefaDoCiclo[];
  idempotency_replayed?: boolean;
}
