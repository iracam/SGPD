export type TarefaStatus = 'PENDENTE' | 'EM_ANALISE' | 'CONCLUIDA' | 'CANCELADA';

export type ProcessoStatus =
  | 'RASCUNHO'
  | 'INICIADO'
  | 'LIBERADO_PARA_RESCISAO'
  | 'RESCISAO_PROCESSADA'
  | 'ENCERRADO'
  | 'CANCELADO';

export type TipoRespostaChecklist =
  | 'BOOLEAN'
  | 'TEXT'
  | 'NUMBER'
  | 'DATE'
  | 'SINGLE_CHOICE'
  | 'MULTIPLE_CHOICE'
  | 'FILE'
  | 'CONFIRMATION';

export interface ItemChecklist {
  id: number;
  code: string;
  question: string;
  response_type: TipoRespostaChecklist;
  is_required: boolean;
  blocks_process: boolean;
  requires_evidence: boolean;
  allows_pending: boolean;
  display_order: number;
  config: { choices?: string[] };
  response: unknown;
  answered_at: string | null;
  evidences: Evidencia[];
}

export interface Evidencia {
  uuid: string;
  process_uuid: string;
  task_id: number;
  pending_uuid: string | null;
  checklist_item_id: number | null;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by: { id: number; username: string };
  uploaded_at: string;
  classification: 'INTERNA' | 'RESTRITA' | 'SENSIVEL';
  download_url: string;
  idempotency_replayed?: boolean;
}

export type PendenciaStatus =
  | 'ABERTA'
  | 'EM_REGULARIZACAO'
  | 'REGULARIZADA'
  | 'ENCAMINHADA_ANALISE'
  | 'CONTESTADA'
  | 'APROVADA_COBRANCA'
  | 'REJEITADA'
  | 'ABONADA'
  | 'ENCERRADA';

export type DecisaoValor = 'APROVADA_COBRANCA' | 'REJEITADA' | 'ABONADA';

export interface PendenciaDecisao {
  id: number;
  decision: DecisaoValor;
  opinion: string;
  decided_by: { id: number; username: string };
  decided_at: string;
  /** Verdadeiro quando o decisor é quem informou o valor (ADR-048). */
  segregation_override: boolean;
}

/** Pretensão de cobrança: o SGPD registra análise, nunca desconto (ADR-009). */
export interface PendenciaValor {
  amount_informed: string | null;
  amount_assessed: string | null;
  amount_contested: string | null;
  amount_approved: string | null;
  /** Só chega preenchido do registro do Senior; a SPA nunca o edita. */
  amount_processed: string | null;
  currency: string;
  justification: string;
  informed_by: { id: number; username: string };
  informed_at: string;
  approved_by: { id: number; username: string } | null;
  approved_at: string | null;
  version: number;
  decisions: PendenciaDecisao[];
}

/** Situações alcançáveis pelo endpoint genérico de situação; o eixo de valor tem serviços próprios. */
export type PendenciaTransicao = Extract<
  PendenciaStatus,
  'ABERTA' | 'EM_REGULARIZACAO' | 'REGULARIZADA' | 'ENCERRADA'
>;

export interface Pendencia {
  uuid: string;
  process_uuid: string;
  task_id: number;
  checklist_item_id: number | null;
  category: string;
  title: string;
  description: string;
  status: PendenciaStatus;
  blocking_level:
    | 'INFORMATIVA'
    | 'NAO_BLOQUEANTE'
    | 'BLOQUEANTE'
    | 'BLOQUEANTE_ATE_DECISAO';
  amount: PendenciaValor | null;
  /** Espelha a autorização do backend: apurar e decidir exigem DP no escopo. */
  can_analyse_amount: boolean;
  identified_at: string;
  regularization_due_at: string | null;
  registered_by: { id: number; username: string };
  version: number;
  items: {
    id: number;
    code: string;
    description: string;
    asset_tag: string;
    serial_number: string;
    quantity: string;
    unit: string;
    item_condition: string;
    extra_data: Record<string, unknown>;
  }[];
  comments: {
    id: number;
    author: { id: number; username: string };
    text: string;
    created_at: string;
  }[];
  idempotency_replayed?: boolean;
}

export interface TarefaSetor {
  id: number;
  status: TarefaStatus;
  sector: { id: number; code: string; name: string; allows_amount: boolean };
  template: { version_id: number; code: string; version_number: number };
  process: {
    uuid: string;
    status: ProcessoStatus;
    company_code: number;
    branch_code: number;
    employee_name: string;
    employee_registration: number;
    due_date: string;
  };
  is_required: boolean;
  blocks_process: boolean;
  sla_hours: number;
  due_at: string;
  started_at: string;
  completed_at: string | null;
  notes: string;
  checklist_item_count: number;
  /** Decidido pelo backend: fora do processo iniciado a tarefa é história. */
  is_actionable: boolean;
  checklist_items: ItemChecklist[];
  pending_items: Pendencia[];
  evidences: Evidencia[];
  version: number;
  idempotency_replayed?: boolean;
}

export interface ListaTarefas {
  offset: number;
  limit: number;
  results: TarefaSetor[];
}

export interface ConcluirTarefaPayload {
  expected_version: number;
  answers: { item_id: number; value: unknown }[];
  notes: string;
}

export interface CriarPendenciaPayload {
  task_id: number;
  expected_task_version: number;
  checklist_item_id: number | null;
  category: string;
  title: string;
  description: string;
  blocking_level: string;
  items: [];
}
