"""System configuration endpoints."""

from django.urls import path

from . import api

app_name = "system-settings-api"

urlpatterns = [
    path(
        "ldap/",
        api.LdapConfigurationView.as_view(),
        name="ldap-configuration",
    ),
    path(
        "ldap/validate/",
        api.LdapConfigurationValidationView.as_view(),
        name="ldap-configuration-validate",
    ),
    path(
        "ldap/certificate/",
        api.LdapCertificateUploadView.as_view(),
        name="ldap-certificate-upload",
    ),
    path(
        "ldap/certificate/validate/",
        api.LdapCertificateValidationView.as_view(),
        name="ldap-certificate-validate",
    ),
    path(
        "email/",
        api.EmailConfigurationView.as_view(),
        name="email-configuration",
    ),
    path(
        "email/validate/",
        api.EmailConfigurationValidationView.as_view(),
        name="email-configuration-validate",
    ),
    path(
        "email/delivery-test/",
        api.EmailDeliveryTestView.as_view(),
        name="email-delivery-test",
    ),
    path(
        "ldap/connection-test/",
        api.LdapConnectionTestView.as_view(),
        name="ldap-connection-test",
    ),
]
