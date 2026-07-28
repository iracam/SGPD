"""Forms for the server-rendered account administration workflow."""

from __future__ import annotations

from typing import Any, cast

from django import forms
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError

from .models import Role, ScopeType
from .services import assignable_permissions


class UserCreateForm(forms.Form):
    username = forms.CharField(label="Login", max_length=150)
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150)
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(label="Senha temporária", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirme a senha", widget=forms.PasswordInput)
    must_change_password = forms.BooleanField(
        label="Exigir alteração de senha no próximo acesso",
        required=False,
        initial=True,
    )
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "As senhas não coincidem.")
        return cleaned_data


class UserUpdateForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput)
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150)
    email = forms.EmailField(label="E-mail")
    is_active = forms.BooleanField(label="Usuário ativo", required=False)
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(label="Nova senha temporária", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirme a senha", widget=forms.PasswordInput)
    must_change_password = forms.BooleanField(
        label="Exigir alteração de senha no próximo acesso",
        required=False,
        initial=True,
    )
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "As senhas não coincidem.")
        return cleaned_data


class ChangeOwnPasswordForm(forms.Form):
    old_password = forms.CharField(label="Senha atual", widget=forms.PasswordInput)
    password1 = forms.CharField(label="Nova senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirme a nova senha", widget=forms.PasswordInput)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "As senhas não coincidem.")
        return cleaned_data


class RoleForm(forms.Form):
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)
    code = forms.CharField(label="Código", max_length=50)
    name = forms.CharField(label="Nome", max_length=120)
    description = forms.CharField(
        label="Descrição",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    is_active = forms.BooleanField(label="Papel ativo", required=False, initial=True)
    permissions = forms.ModelMultipleChoiceField(
        label="Permissões",
        queryset=Permission.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args: Any, is_create: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        permissions_field = cast(
            "forms.ModelMultipleChoiceField[Permission]",
            self.fields["permissions"],
        )
        permissions_field.queryset = assignable_permissions().order_by("codename")
        if not is_create:
            self.fields["code"].disabled = True


class RoleAssignmentForm(forms.Form):
    role = forms.ModelChoiceField(
        label="Papel",
        queryset=Role.objects.none(),
    )
    scope_type = forms.ChoiceField(label="Escopo", choices=ScopeType.choices)
    company_code = forms.IntegerField(label="Empresa", min_value=1, required=False)
    branch_code = forms.IntegerField(label="Filial", min_value=1, required=False)
    valid_from = forms.DateTimeField(
        label="Válido desde",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    valid_until = forms.DateTimeField(
        label="Válido até",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        role_field = cast("forms.ModelChoiceField[Role]", self.fields["role"])
        role_field.queryset = Role.objects.filter(is_active=True).order_by("code")

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        scope_type = cleaned_data.get("scope_type")
        company_code = cleaned_data.get("company_code")
        branch_code = cleaned_data.get("branch_code")
        if scope_type == ScopeType.GLOBAL and (company_code or branch_code):
            raise ValidationError("O escopo global não aceita empresa ou filial.")
        if scope_type == ScopeType.COMPANY and (not company_code or branch_code):
            raise ValidationError("Informe somente a empresa para esse escopo.")
        if scope_type == ScopeType.BRANCH and (not company_code or not branch_code):
            raise ValidationError("Informe empresa e filial para esse escopo.")
        return cleaned_data


class AdLinkForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput)
    identifier = forms.CharField(
        label="Identificador imutável no AD",
        max_length=255,
        help_text="Valor opaco homologado pela Infraestrutura; não use apenas o e-mail.",
    )
    username = forms.CharField(label="Usuário no AD", max_length=150)
    confirmed = forms.BooleanField(
        label="Confirmo que a identidade foi conferida administrativamente no AD",
    )
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))


class ReasonVersionForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput)
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))
