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
