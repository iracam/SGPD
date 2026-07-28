"""X.509 validation and canonicalization for the LDAP CA bundle."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from django.utils import timezone

from .exceptions import CertificateValidationError

MAX_CERTIFICATE_BYTES = 512 * 1024


@dataclass(frozen=True, slots=True)
class CertificateBundleInfo:
    pem_bytes: bytes
    sha256: str
    subject: str
    issuer: str
    not_before: datetime
    not_after: datetime
    certificate_count: int


def validate_certificate_bundle(data: bytes) -> CertificateBundleInfo:
    if not data:
        raise CertificateValidationError("O arquivo de certificado está vazio.")
    if len(data) > MAX_CERTIFICATE_BYTES:
        raise CertificateValidationError("O certificado deve ter no máximo 512 KiB.")

    try:
        certificates = list(x509.load_pem_x509_certificates(data))
    except ValueError:
        try:
            certificates = [x509.load_der_x509_certificate(data)]
        except ValueError as exc:
            raise CertificateValidationError(
                "O arquivo não contém um certificado X.509 PEM ou DER válido."
            ) from exc
    if not certificates:
        raise CertificateValidationError("O bundle não contém certificados X.509.")

    now = timezone.now()
    for certificate in certificates:
        try:
            constraints = certificate.extensions.get_extension_for_class(
                x509.BasicConstraints
            ).value
        except x509.ExtensionNotFound as exc:
            raise CertificateValidationError(
                "Todo certificado do bundle deve declarar Basic Constraints de CA."
            ) from exc
        if not constraints.ca:
            raise CertificateValidationError(
                "O bundle deve conter apenas certificados de autoridade certificadora."
            )
        if certificate.not_valid_before_utc > now:
            raise CertificateValidationError("O certificado ainda não está válido.")
        if certificate.not_valid_after_utc <= now:
            raise CertificateValidationError("O certificado está expirado.")

    pem_bytes = b"".join(
        certificate.public_bytes(serialization.Encoding.PEM) for certificate in certificates
    )
    return CertificateBundleInfo(
        pem_bytes=pem_bytes,
        sha256=hashlib.sha256(pem_bytes).hexdigest(),
        subject=certificates[0].subject.rfc4514_string(),
        issuer=certificates[0].issuer.rfc4514_string(),
        not_before=max(item.not_valid_before_utc for item in certificates),
        not_after=min(item.not_valid_after_utc for item in certificates),
        certificate_count=len(certificates),
    )


def validate_certificate_path(path: str | Path) -> CertificateBundleInfo:
    certificate_path = Path(path)
    try:
        data = certificate_path.read_bytes()
    except (OSError, ValueError) as exc:
        raise CertificateValidationError(
            "O arquivo de certificado configurado não pôde ser lido."
        ) from exc
    return validate_certificate_bundle(data)
