/** Relatórios mínimos do RF-036. Somente leitura. */

export interface PeriodoRelatorio {
  start: string;
  end: string;
}

export interface LinhaContagem {
  key: string;
  label: string;
  total: number;
  /** Recorte secundário da linha — bloqueantes, por exemplo. */
  detail: number;
}

export interface LinhaDuracao {
  key: string;
  label: string;
  total: number;
  average_hours: number | null;
}

export interface LinhaValor {
  currency: string;
  informed: string;
  approved: string;
  undecided: number;
}

export interface LinhaVencido {
  process_uuid: string;
  process_ref: string;
  employee_name: string;
  company_code: number;
  branch_code: number;
  due_date: string;
  days_overdue: number;
  open_tasks: number;
}

export interface TempoCiclo {
  processes: number;
  average_days: number | null;
  median_days: number | null;
}

export interface Relatorios {
  period: PeriodoRelatorio;
  process_cycle_time: TempoCiclo;
  sector_cycle_time: LinhaDuracao[];
  pending_by_category: LinhaContagem[];
  processes_by_company: LinhaContagem[];
  overdue_processes: { total: number; results: LinhaVencido[] };
  sector_delays: LinhaDuracao[];
  amounts: LinhaValor[];
  released_processes: { total: number; results: LinhaContagem[] };
}
