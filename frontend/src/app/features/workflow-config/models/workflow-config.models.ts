export type TipoRespostaChecklist =
  | 'BOOLEAN'
  | 'TEXT'
  | 'NUMBER'
  | 'DATE'
  | 'SINGLE_CHOICE'
  | 'MULTIPLE_CHOICE'
  | 'FILE'
  | 'CONFIRMATION';

export interface SetorWorkflow {
  id: number;
  code: string;
  name: string;
  default_due_hours: number;
}

export interface ItemTemplate {
  id: number;
  code: string;
  question: string;
  response_type: TipoRespostaChecklist;
  is_required: boolean;
  blocks_process: boolean;
  requires_evidence: boolean;
  allows_pending: boolean;
  display_order: number;
  config: Record<string, unknown>;
}

export interface VersaoTemplate {
  id: number;
  version_number: number;
  status: 'DRAFT' | 'PUBLISHED' | 'RETIRED';
  default_due_hours: number | null;
  created_at: string;
  published_at: string | null;
  items: ItemTemplate[];
}

export interface TemplateChecklist {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  sector: { id: number; code: string; name: string };
  current_version_id: number | null;
  version: number;
  versions: VersaoTemplate[];
}

export interface RegraGrupo {
  id: number;
  sector: { id: number; code: string; name: string };
  template_version: {
    id: number;
    template_id: number;
    template_code: string;
    version_number: number;
    status: 'DRAFT' | 'PUBLISHED' | 'RETIRED';
  };
  is_required: boolean;
  blocks_process: boolean;
  due_hours_override: number | null;
  display_order: number;
}

export interface VersaoGrupo {
  id: number;
  version_number: number;
  status: 'DRAFT' | 'PUBLISHED' | 'RETIRED';
  created_at: string;
  published_at: string | null;
  sectors: RegraGrupo[];
}

export interface GrupoValidacao {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  current_version_id: number | null;
  version: number;
  versions: VersaoGrupo[];
}

export interface PaginaWorkflow<T> {
  results: T[];
}

export interface NovoTemplate {
  code: string;
  sector_id: number;
  name: string;
  description: string;
  default_due_hours: number | null;
  items: Array<Omit<ItemTemplate, 'id'>>;
}

export interface NovoGrupo {
  code: string;
  name: string;
  description: string;
  sectors: Array<{
    sector_id: number;
    template_version_id: number;
    is_required: boolean;
    blocks_process: boolean;
    due_hours_override: number | null;
    display_order: number;
  }>;
}
