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
    processManagerCandidates: '/api/v1/processes/manager-candidates/',
    tasks: '/api/v1/tasks/',
    workflowTemplates: '/api/v1/workflow-config/templates/',
    workflowGroups: '/api/v1/workflow-config/groups/',
    workflowSectors: '/api/v1/workflow-config/sectors/',

    sectors: '/api/v1/sectors/',
    sectorResponsibleCandidates: '/api/v1/sectors/responsible-candidates/',

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
