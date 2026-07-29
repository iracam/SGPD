export type TipoEscopoSetor = 'GLOBAL' | 'COMPANY' | 'BRANCH';

export interface EscopoSetor {
  scope_type: TipoEscopoSetor;
  company_code: number | null;
  branch_code: number | null;
  scope_key: string;
}

export interface SetorResumido {
  id: number;
  code: string;
  name: string;
}

export interface UsuarioResponsavelCandidato {
  id: number;
  username: string;
  display_name: string;
  email: string;
  is_active: boolean;
}

export interface ResponsavelSetor {
  id: number;
  user: UsuarioResponsavelCandidato;
  valid_from: string;
  valid_until: string | null;
  is_active: boolean;
  is_effective: boolean;
  is_scheduled: boolean;
  inherited_scopes: EscopoSetor[];
  assigned_at: string;
  updated_at: string;
  version: number;
}

export interface Setor {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  default_due_hours: number;
  blocks_process: boolean;
  allows_amount: boolean;
  requires_evidence: boolean;
  escalation_sector: SetorResumido | null;
  scopes: EscopoSetor[];
  responsibles: ResponsavelSetor[];
  effective_responsible_count: number;
  scheduled_responsible_count: number;
  has_effective_responsible: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface EscopoSetorEntrada {
  scope_type: TipoEscopoSetor;
  company_code: number | null;
  branch_code: number | null;
}

export interface ResponsavelSetorEntrada {
  user_id: number;
  valid_from?: string;
  valid_until: string | null;
}

export interface NovoSetor {
  name: string;
  description: string;
  default_due_hours: number;
  blocks_process: boolean;
  allows_amount: boolean;
  requires_evidence: boolean;
  escalation_sector_id: number | null;
  scopes: EscopoSetorEntrada[];
  responsibles: ResponsavelSetorEntrada[];
}

export interface EdicaoSetor extends NovoSetor {
  version: number;
  is_active: boolean;
}
