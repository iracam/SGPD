/** Indicadores do painel (RF-034, RF-035). Somente leitura. */

export interface ContagemRotulada {
  key: string;
  label: string;
  total: number;
}

export interface TotalMoeda {
  currency: string;
  /** Decimal como string: `float` não é dinheiro. */
  informed: string;
}

export interface ProcessoCritico {
  process_uuid: string;
  process_ref: string;
  employee_name: string;
  company_code: number;
  branch_code: number;
  due_date: string;
  overdue_tasks: number;
}

export interface IndicadoresCoordenacao {
  open_processes: number;
  completed_processes: number;
  draft_processes: number;
  cancelled_processes: number;
  overdue_processes: number;
  due_soon_processes: number;
  open_pending_items: number;
  blocking_pending_items: number;
  amounts_awaiting_decision: number;
  by_status: ContagemRotulada[];
  delayed_sectors: ContagemRotulada[];
  amount_totals: TotalMoeda[];
  critical_processes: ProcessoCritico[];
}

export interface IndicadoresSetor {
  pending_tasks: number;
  overdue_tasks: number;
  due_soon_tasks: number;
  by_company: ContagemRotulada[];
  by_branch: ContagemRotulada[];
  critical_processes: ProcessoCritico[];
}

export interface Indicadores {
  generated_at: string;
  coordination: IndicadoresCoordenacao | null;
  sector: IndicadoresSetor | null;
}
