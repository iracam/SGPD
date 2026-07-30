"""Private evidence storage, never exposed as static or media URLs."""

from django.core.files.storage import Storage, storages


def evidence_storage() -> Storage:
    return storages["evidence"]
