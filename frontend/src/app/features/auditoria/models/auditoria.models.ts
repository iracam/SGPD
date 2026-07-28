export interface EventoAuditoria {
  uuid: string;
  event_type: string;
  actor: string | null;
  target_user: string | null;
  entity_type: string;
  entity_id: string;
  occurred_at: string | null;
  reason: string;
  changes: Record<string, unknown>;
  correlation_id: string;
}
