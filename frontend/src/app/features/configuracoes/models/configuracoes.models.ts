export interface LdapCertificateStatus {
  configured: boolean;
  source: 'database' | 'environment' | null;
  original_name: string | null;
  sha256: string | null;
  subject: string | null;
  issuer: string | null;
  not_before: string | null;
  not_after: string | null;
  certificate_count: number;
  valid: boolean;
  errors: string[];
}

export interface LdapConnectionStatus {
  tested_at: string | null;
  success: boolean | null;
  duration_ms: number | null;
  tested_by: string | null;
}

export interface LdapConfiguration {
  source: 'database' | 'environment';
  version: number;
  enabled: boolean;
  authentication_enabled: boolean;
  server_address: string;
  use_tls: boolean;
  bind_dn: string;
  bind_password_configured: boolean;
  user_search_base: string;
  group_search_base: string;
  required_group_dn: string;
  tls_require_certificate: boolean;
  connect_timeout_seconds: number;
  receive_timeout_seconds: number;
  page_size: number;
  result_limit: number;
  nested_group_search: boolean;
  local_superuser_fallback: boolean;
  user_extra_filter: string;
  secure_transport: boolean;
  validation: {
    valid: boolean;
    errors: string[];
  };
  certificate: LdapCertificateStatus;
  connection_test: LdapConnectionStatus;
  updated_at: string | null;
  updated_by: string | null;
}

export interface LdapConfigurationPayload {
  version: number;
  enabled: boolean;
  authentication_enabled: boolean;
  server_address: string;
  use_tls: boolean;
  bind_dn: string;
  bind_password: string;
  user_search_base: string;
  group_search_base: string;
  required_group_dn: string;
  connect_timeout_seconds: number;
  receive_timeout_seconds: number;
  page_size: number;
  result_limit: number;
  nested_group_search: boolean;
  local_superuser_fallback: boolean;
  user_extra_filter: string;
}

export interface LdapDirectoryGroup {
  distinguished_name: string;
  name: string;
  account_name: string | null;
  description: string | null;
}

export interface LdapDirectoryPage<T> {
  limit: number;
  results: T[];
}

export interface LdapValidationResult {
  valid: boolean;
  errors: string[];
}

export interface LdapCertificateValidationResult {
  valid: boolean;
  source: 'database' | 'environment';
  sha256: string;
  subject: string;
  issuer: string;
  not_before: string;
  not_after: string;
  certificate_count: number;
}

export interface LdapConnectionTestResult {
  success: boolean;
  secure_transport: boolean;
  user_search_base_source: 'configured' | 'root_dse';
  group_search_base_source: 'configured' | 'root_dse';
  duration_ms: number;
  tested_at: string;
}

export interface EmailValidationResult {
  readonly valid: boolean;
  readonly errors: readonly string[];
  readonly warnings: readonly string[];
}

export interface EmailDeliveryTest {
  readonly tested_at: string | null;
  readonly success: boolean | null;
  readonly recipient: string | null;
  readonly error: string | null;
  readonly tested_by: string | null;
}

export interface EmailConfigurationPayload {
  readonly version: number;
  readonly enabled: boolean;
  readonly host: string;
  readonly port: number;
  readonly use_tls: boolean;
  readonly username: string;
  readonly password?: string;
  readonly timeout_seconds: number;
  readonly default_from_email: string;
  readonly base_url: string;
  readonly max_attempts: number;
  readonly batch_size: number;
  readonly stale_minutes: number;
  readonly task_due_soon_hours: number;
  readonly task_due_imminent_hours: number;
  readonly task_critical_hours: number;
  readonly process_due_soon_hours: number;
}

export interface EmailConfiguration extends Omit<EmailConfigurationPayload, 'password'> {
  readonly source: string;
  readonly password_configured: boolean;
  readonly validation: EmailValidationResult;
  readonly delivery_test: EmailDeliveryTest;
  readonly updated_at: string | null;
  readonly updated_by: string | null;
}

export interface EmailDeliveryTestResult {
  readonly success: boolean;
  readonly recipient: string;
  readonly tested_at: string;
}
