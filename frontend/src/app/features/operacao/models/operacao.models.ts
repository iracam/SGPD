/** Sonda operacional: fila, armazenamento e retenção (R63, RNF-009). */

export interface FilaOperacional {
  counts: Record<string, number>;
  oldest_pending_at: string | null;
  last_sent_at: string | null;
  stale_minutes: number;
  is_stalled: boolean;
  verdict: string;
}

export interface ArmazenamentoOperacional {
  evidence_count: number;
  evidence_bytes: number;
}

export interface RetencaoOperacional {
  closed_processes: number;
  beyond_retention: number;
  oldest_closed_at: string | null;
  retention_years: number;
}

export interface Operacao {
  checked_at: string;
  queue: FilaOperacional;
  storage: ArmazenamentoOperacional;
  retention: RetencaoOperacional;
}
