export type ProcessoStatus =
  | 'RASCUNHO'
  | 'INICIADO'
  | 'LIBERADO_PARA_RESCISAO'
  | 'RESCISAO_PROCESSADA'
  | 'ENCERRADO'
  | 'CANCELADO';

export interface ProcessoResumo {
  uuid: string;
  status: ProcessoStatus;
  company_code: number;
  branch_code: number;
  employee_type_code: number;
  employee_registration: number;
  opened_at: string;
  completion_at: string | null;
  planned_termination_date: string;
  due_date: string;
  priority: string;
  version: number;
  employee_snapshot: {
    employee_name: string;
    registration: number;
    branch_legal_name: string;
  };
}

export interface ListaProcessos {
  offset: number;
  limit: number;
  results: ProcessoResumo[];
}

export interface TarefaProcesso {
  id: number;
  status: 'PENDENTE' | 'EM_ANALISE' | 'CONCLUIDA' | 'CANCELADA';
  sector: { id: number; code: string; name: string };
  template: { version_id: number; code: string; version_number: number };
  due_at: string;
  completed_at: string | null;
}

export interface ListaTarefasProcesso {
  offset: number;
  limit: number;
  results: TarefaProcesso[];
}
