export interface Paginado<T> {
  offset: number;
  limit: number;
  results: T[];
}

export interface Usuario {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  must_change_password: boolean;
  is_superuser: boolean;
  is_active: boolean;
  version: number;
  date_joined: string | null;
  last_login: string | null;
  ad_identifier: string | null;
  ad_username: string | null;
  ad_linked_at: string | null;
  ad_linked_by: string | null;
  ad_authentication_enabled: boolean;
  local_password_allowed: boolean;
}

export interface Atribuicao {
  id: number;
  user_id: number;
  role: { id: number; code: string };
  scope_type: 'GLOBAL' | 'COMPANY' | 'BRANCH';
  company_code: number | null;
  branch_code: number | null;
  scope_key: string;
  valid_from: string | null;
  valid_until: string | null;
  is_active: boolean;
  assigned_by: string | null;
  assigned_at: string | null;
  revoked_by: string | null;
  revoked_at: string | null;
}

export interface UsuarioDetalhe extends Usuario {
  role_assignments: Atribuicao[];
}

export interface NovoUsuario {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  password_confirm: string;
  must_change_password: boolean;
  reason: string;
}

export interface EdicaoUsuario {
  version: number;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
  reason: string;
}

export interface RedefinicaoSenha {
  password: string;
  password_confirm: string;
  must_change_password: boolean;
  reason: string;
}

export interface NovaAtribuicao {
  role_id: number;
  scope_type: 'GLOBAL' | 'COMPANY' | 'BRANCH';
  company_code: number | null;
  branch_code: number | null;
  valid_until: string | null;
  reason: string;
}

export interface VinculoAd {
  version: number;
  identifier: string;
  username: string;
  reason: string;
}

export interface DiretorioStatus {
  enabled: boolean;
  authentication_enabled: boolean;
  configured: boolean;
  secure_transport: boolean;
  insecure_transport: boolean;
  user_search_base_configured: boolean;
  group_search_base_configured: boolean;
  required_group_configured: boolean;
  errors: string[];
}

export interface UsuarioDiretorio {
  identifier: string;
  username: string;
  user_principal_name: string | null;
  first_name: string | null;
  last_name: string | null;
  display_name: string;
  email: string | null;
  distinguished_name: string;
  can_import: boolean;
  missing_import_fields: string[];
  local_user: { id: number; username: string } | null;
  username_conflict: { id: number; username: string } | null;
  email_conflict: { id: number; username: string } | null;
}

export interface PaginaDiretorio<T> {
  limit: number;
  results: T[];
}
