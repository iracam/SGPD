/** Todas as rotas da API em um único lugar, tipadas. */
export const apiConfig = {
  routes: {
    authCsrf: '/api/v1/auth/csrf/',
    authLogin: '/api/v1/auth/login/',
    authLogout: '/api/v1/auth/logout/',
    authMe: '/api/v1/auth/me/',
    authContext: '/api/v1/auth/context/',
    authChangePassword: '/api/v1/auth/change-password/',

    accountsUsers: '/api/v1/accounts/users/',
    accountsRoles: '/api/v1/accounts/roles/',
    accountsAudit: '/api/v1/accounts/audit/',
    accountsRoleAssignments: '/api/v1/accounts/role-assignments/',
    accountsDirectoryStatus: '/api/v1/accounts/directory/status/',
    accountsDirectoryUsers: '/api/v1/accounts/directory/users/',
    accountsDirectoryGroups: '/api/v1/accounts/directory/groups/',
    accountsDirectoryUserCreate: '/api/v1/accounts/directory/users/create/',

    processes: '/api/v1/processes/',
    tasks: '/api/v1/tasks/',
    pendingItems: '/api/v1/pending-items/',
    evidence: '/api/v1/evidence/',
    notifications: '/api/v1/notifications/',
    reportingDashboard: '/api/v1/reporting/dashboard/',
    workflowTemplates: '/api/v1/workflow-config/templates/',
    workflowGroups: '/api/v1/workflow-config/groups/',
    workflowSectors: '/api/v1/workflow-config/sectors/',
    workflowApplicabilityRules: '/api/v1/workflow-config/applicability-rules/',

    sectors: '/api/v1/sectors/',
    sectorResponsibleCandidates: '/api/v1/sectors/responsible-candidates/',

    settingsEmail: '/api/v1/settings/email/',
    settingsEmailValidate: '/api/v1/settings/email/validate/',
    settingsEmailDeliveryTest: '/api/v1/settings/email/delivery-test/',
    settingsLdap: '/api/v1/settings/ldap/',
    settingsLdapValidate: '/api/v1/settings/ldap/validate/',
    settingsLdapCertificate: '/api/v1/settings/ldap/certificate/',
    settingsLdapCertificateValidate: '/api/v1/settings/ldap/certificate/validate/',
    settingsLdapConnectionTest: '/api/v1/settings/ldap/connection-test/',

    referenceCompanies: '/api/v1/references/companies/',
    referenceBranches: '/api/v1/references/branches/',
    referenceEmployeeTypes: '/api/v1/references/employee-types/',
    referenceEmployees: '/api/v1/references/employees/',
  },
} as const;
