"""Private storage selector for uploaded configuration assets."""

from django.core.files.storage import Storage, storages


def system_configuration_storage() -> Storage:
    return storages["system_configuration"]
