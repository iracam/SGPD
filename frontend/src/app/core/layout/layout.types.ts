import { PermissionKey } from '../auth/models/auth.models';

export interface NavItem {
  label: string;
  route: string;
  icon: string;
  description: string;
  /** Ausente significa visível para qualquer sessão autenticada. */
  feature?: PermissionKey;
  /** Papel funcional explícito; não é satisfeito por SuperAdmin. */
  role?: string;
}
