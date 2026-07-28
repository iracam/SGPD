"""Safe failures exposed by the Active Directory boundary."""


class ActiveDirectoryError(Exception):
    """Base error whose message never contains driver or credential details."""


class DirectoryConfigurationError(ActiveDirectoryError):
    """The integration is disabled or has an invalid contract."""


class DirectoryUnavailableError(ActiveDirectoryError):
    """The directory could not be reached or bound safely."""


class DirectoryContractError(ActiveDirectoryError):
    """The directory returned an entry outside the homologated contract."""


class DirectoryIdentityNotFoundError(ActiveDirectoryError):
    """No eligible identity matched the stable identifier."""
