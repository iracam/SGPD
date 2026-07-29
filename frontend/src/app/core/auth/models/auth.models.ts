export interface AuthUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  must_change_password: boolean;
  is_superuser: boolean;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
  new_password_confirm: string;
}

/** Envelope de erro da API: {code, message, details}. */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[] | string>;
}

export type PermissionKey =
  | 'manage_users'
  | 'manage_roles'
  | 'link_ad_identity'
  | 'view_account_audit'
  | 'query_senior_references'
  | 'manage_sectors';

export interface PermissionGrant {
  granted: boolean;
  /** `null` significa todas as empresas; uma lista significa exatamente essas. */
  companies: number[] | null;
}

export interface ScopeAssignment {
  role: string;
  scope_type: 'GLOBAL' | 'COMPANY' | 'BRANCH';
  company_code: number | null;
  branch_code: number | null;
  valid_until: string | null;
}

export interface AuthContext {
  user: AuthUser;
  roles: string[];
  permissions: Record<PermissionKey, PermissionGrant>;
  scopes: {
    is_superuser: boolean;
    assignments: ScopeAssignment[];
  };
  features: Record<PermissionKey, { can_view: boolean }>;
  meta: {
    policy: string;
    server_time: string;
  };
}
