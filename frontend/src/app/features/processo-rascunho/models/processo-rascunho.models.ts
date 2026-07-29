export interface ProcessoRascunhoResumo {
  uuid: string;
  status: 'RASCUNHO' | 'INICIADO';
  company_code: number;
  branch_code: number;
  employee_registration: number;
  opened_at: string;
  started_at: string | null;
  due_date: string;
  version: number;
  employee_snapshot: {
    employee_name: string;
    registration: number;
  };
}

export interface GrupoDisponivel {
  version_id: number;
  group_id: number;
  code: string;
  name: string;
  description: string;
  version_number: number;
  sectors: Array<{
    id: number;
    code: string;
    name: string;
    is_required: boolean;
    blocks_process: boolean;
    template_version_id: number;
    template_code: number;
    template_version_number: number;
  }>;
}

export interface AjusteSetorRascunho {
  sector_id: number;
  sector_code: string;
  action: 'INCLUDE' | 'EXCLUDE';
  template_version_id: number | null;
  is_required: boolean;
  blocks_process: boolean;
  due_hours_override: number | null;
  reason: string;
}

export interface SetorResolvidoRascunho {
  sector_id: number;
  code: string;
  name: string;
  template_version_id: number;
  template_code: number;
  template_version_number: number;
  is_required: boolean;
  blocks_process: boolean;
  sla_hours: number;
  source: 'GROUP' | 'MANUAL';
}

export interface TarefaSetor {
  id: number;
  status: 'PENDENTE';
  sector: { id: number; code: string; name: string };
  template: { version_id: number; code: string; version_number: number };
  is_required: boolean;
  blocks_process: boolean;
  sla_hours: number;
  due_at: string;
  started_at: string;
  checklist_item_count: number;
  version: number;
}

export interface ContextoRascunho {
  process: ProcessoRascunhoResumo;
  selection: {
    group_version_ids: number[];
    groups: Array<{
      version_id: number;
      code: string;
      name: string;
      version_number: number;
    }>;
    overrides: AjusteSetorRascunho[];
    resolved_sectors: SetorResolvidoRascunho[];
    blockers: string[];
  };
  available_groups: GrupoDisponivel[];
  tasks: TarefaSetor[];
  idempotency_replayed?: boolean;
}

export interface AtualizacaoSelecaoRascunho {
  expected_version: number;
  group_version_ids: number[];
  overrides: Array<Omit<AjusteSetorRascunho, 'sector_code'>>;
}
