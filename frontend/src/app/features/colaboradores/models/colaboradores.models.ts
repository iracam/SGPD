export interface PaginaSenior<T> {
  offset: number;
  limit: number;
  results: T[];
}

export interface EmpresaSenior {
  company: number;
}

export interface FilialSenior {
  company: number;
  branch: number;
  legal_name: string;
}

export interface TipoColaboradorSenior {
  employee_type: number;
  description: string;
}

export interface ColaboradorSenior {
  company: number;
  branch: number;
  legal_name: string;
  employee_type: number;
  employee_type_description: string;
  registration: number;
  name: string;
  admission_date: string;
  leave_code: number;
  leave_description: string;
  leave_date: string | null;
  job_structure: number;
  job_code: string;
  job_description: string;
  cost_center: string;
  cost_center_description: string | null;
  source_updated_at: string | null;
}

export interface NovaAberturaProcesso {
  company_code: number;
  branch_code: number;
  employee_type_code: number;
  employee_registration: number;
  planned_termination_date: string;
  due_date: string;
  reason: string;
  priority: string;
  notes: string;
}

export interface ProcessoAberto {
  uuid: string;
  status: 'RASCUNHO';
  company_code: number;
  branch_code: number;
  employee_type_code: number;
  employee_registration: number;
  opened_by: {
    id: number;
    username: string;
  };
  opened_at: string;
  planned_termination_date: string;
  due_date: string;
  reason: string;
  priority: string;
  notes: string;
  version: number;
  employee_snapshot: {
    employee_name: string;
    registration: number;
    source_queried_at: string;
  };
}
