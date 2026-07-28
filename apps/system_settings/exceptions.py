"""Safe failures raised by system-configuration services."""


class ConfigurationSecretError(Exception):
    """An encrypted configuration secret cannot be safely used."""


class CertificateValidationError(Exception):
    """An uploaded or persisted certificate bundle is invalid."""
