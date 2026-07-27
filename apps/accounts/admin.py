from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SGPDUserAdmin(UserAdmin):  # type: ignore[type-arg]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Informações pessoais",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                )
            },
        ),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
        (
            "Identidade corporativa futura",
            {
                "fields": (
                    "ad_identifier",
                    "ad_username",
                    "ad_linked_at",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                ),
            },
        ),
        (
            "Cadastro SGPD",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                )
            },
        ),
    )
