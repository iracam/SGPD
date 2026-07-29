export type TarefaStatus = 'PENDENTE' | 'EM_ANALISE' | 'CONCLUIDA';

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
}

export interface TarefaSetor {
  id: number;
  status: TarefaStatus;
  sector: { id: number; code: string; name: string };
  template: { version_id: number; code: string; version_number: number };
  process: {
    uuid: string;
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
  checklist_items: ItemChecklist[];
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
