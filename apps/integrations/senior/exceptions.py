"""Errors exposed by the Senior HCM integration boundary."""


class SeniorIntegrationError(Exception):
    """Base error for the read-only Senior integration."""


class SeniorQueryValidationError(SeniorIntegrationError, ValueError):
    """A query argument violates the public repository contract."""


class SeniorUnavailableError(SeniorIntegrationError):
    """The Senior data source could not answer safely."""


class SeniorContractError(SeniorIntegrationError):
    """The Senior result does not match the homologated contract."""
