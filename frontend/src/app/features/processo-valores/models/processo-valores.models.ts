import {
  DecisaoValor,
  PendenciaStatus,
  PendenciaValor,
} from '../../tarefas/models/tarefas.models';

export interface TotalPorMoeda {
  currency: string;
  informed: string;
  assessed: string;
  contested: string;
  approved: string;
  processed: string;
}

export interface ValorDoProcesso {
  uuid: string;
  title: string;
  status: PendenciaStatus;
  blocking_level: string;
  task_id: number;
  sector: { id: number; code: string; name: string };
  amount: PendenciaValor | null;
}

/** Decisão tomada por quem informou o valor: a ADR-048 exige separá-la na conferência. */
export interface DecisaoSegregada {
  id: number;
  pending_uuid: string;
  pending_title: string;
  decision: DecisaoValor;
  opinion: string;
  decided_by: { id: number; username: string };
  decided_at: string;
}

export interface ConsolidacaoValores {
  process: {
    uuid: string;
    status: string;
    company_code: number;
    branch_code: number;
    employee_name: string;
    employee_registration: number;
  };
  totals: TotalPorMoeda[];
  undecided_count: number;
  pending_items: ValorDoProcesso[];
  segregation_overrides: DecisaoSegregada[];
}
