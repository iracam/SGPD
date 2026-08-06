/** Sonda operacional: fila, armazenamento e retenção (R63, RNF-009). */

export interface FilaOperacional {
  counts: Record<string, number>;
  oldest_pending_at: string | null;
  last_sent_at: string | null;
  stale_minutes: number;
  is_stalled: boolean;
  verdict: string;
}

/**
 * Batimento do agendamento (ADR-057).
 *
 * Quem grava é a tarefa periódica do Beat; quem lê é o processo web. É o que
 * denuncia o agendamento parado mesmo com a fila vazia.
 */
export interface AgendamentoOperacional {
  last_beat_at: string | null;
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
  scheduler: AgendamentoOperacional;
  storage: ArmazenamentoOperacional;
  retention: RetencaoOperacional;
}
