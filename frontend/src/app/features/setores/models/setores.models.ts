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
  version: number;
  created_at: string;
  updated_at: string;
}

export interface EscopoSetorEntrada {
  scope_type: TipoEscopoSetor;
  company_code: number | null;
  branch_code: number | null;
}

export interface NovoSetor {
  code: string;
  name: string;
  description: string;
  default_due_hours: number;
  blocks_process: boolean;
  allows_amount: boolean;
  requires_evidence: boolean;
  escalation_sector_id: number | null;
  scopes: EscopoSetorEntrada[];
  reason: string;
}

export interface EdicaoSetor extends Omit<NovoSetor, 'code'> {
  version: number;
  is_active: boolean;
}
