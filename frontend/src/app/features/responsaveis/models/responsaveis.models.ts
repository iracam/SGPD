import { TipoEscopoSetor } from '../../setores/models/setores.models';

export interface ResponsabilidadeSetorResumo {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
}

export interface ResponsabilidadeUsuarioResumo {
  id: number;
  username: string;
  display_name: string;
  email: string;
  is_active: boolean;
}

export interface EscopoPapelResponsavel {
  scope_type: TipoEscopoSetor;
  company_code: number | null;
  branch_code: number | null;
  scope_key: string;
  valid_from: string;
  valid_until: string | null;
}

export interface CandidatoResponsavel {
  id: number;
  username: string;
  display_name: string;
  email: string;
  role_scopes: EscopoPapelResponsavel[];
}

export interface ResponsabilidadeSetor {
  id: number;
  sector: ResponsabilidadeSetorResumo;
  user: ResponsabilidadeUsuarioResumo;
  scope_type: TipoEscopoSetor;
  company_code: number | null;
  branch_code: number | null;
  scope_key: string;
  valid_from: string;
  valid_until: string | null;
  is_active: boolean;
  is_effective: boolean;
  assigned_at: string;
  updated_at: string;
  revoked_at: string | null;
  version: number;
}

export interface NovaResponsabilidadeSetor {
  sector_id: number;
  user_id: number;
  scope_type: TipoEscopoSetor;
  company_code: number | null;
  branch_code: number | null;
  valid_from: string;
  valid_until: string | null;
  reason: string;
}

export interface EdicaoResponsabilidadeSetor {
  version: number;
  valid_from: string;
  valid_until: string | null;
  reason: string;
}

export interface RevogacaoResponsabilidadeSetor {
  version: number;
  reason: string;
}
