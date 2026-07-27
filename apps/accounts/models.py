"""SGPD-owned users and future AD identity links."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("e-mail", unique=True)
    ad_identifier = models.CharField(
        "identificador imutável no AD",
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    ad_username = models.CharField("usuário no AD", max_length=150, blank=True)
    ad_linked_at = models.DateTimeField("vinculado ao AD em", null=True, blank=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self) -> str:
        return self.get_full_name() or self.username
