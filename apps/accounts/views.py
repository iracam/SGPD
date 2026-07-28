"""Server-rendered account and role administration."""

from __future__ import annotations

from typing import cast

from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .authorization import permission_required
from .forms import (
    AdLinkForm,
    ChangeOwnPasswordForm,
    ReasonForm,
    ReasonVersionForm,
    ResetPasswordForm,
    RoleAssignmentForm,
    RoleForm,
    UserCreateForm,
    UserUpdateForm,
)
from .models import (
    AccountAuditEvent,
    AccountEventType,
    Role,
    RoleAssignment,
    ScopeType,
    User,
)
from .services import (
    AssignRoleCommand,
    AssignRoleService,
    ChangeOwnPasswordCommand,
    ChangeOwnPasswordService,
    CreateRoleCommand,
    CreateRoleService,
    CreateUserCommand,
    CreateUserService,
    LinkAdIdentityCommand,
    LinkAdIdentityService,
    ResetPasswordCommand,
    ResetPasswordService,
    RevokeRoleCommand,
    RevokeRoleService,
    UnlinkAdIdentityCommand,
    UnlinkAdIdentityService,
    UpdateRoleCommand,
    UpdateRoleService,
    UpdateUserCommand,
    UpdateUserService,
    record_authentication_event,
)


class SGPDLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        user = cast(User, self.request.user)
        if user.must_change_password:
            return reverse("accounts:change-own-password")
        return super().get_success_url()

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        response = super().form_valid(form)
        record_authentication_event(
            event_type=AccountEventType.LOGIN,
            user=cast(User, self.request.user),
            reason="Autenticação local concluída.",
        )
        return response

    def form_invalid(self, form: AuthenticationForm) -> HttpResponse:
        record_authentication_event(
            event_type=AccountEventType.LOGIN_FAILED,
            user=None,
            reason="Tentativa de autenticação local rejeitada.",
        )
        return super().form_invalid(form)


class SGPDLogoutView(LogoutView):
    next_page = "/accounts/login/"

    def post(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        user = cast(User, request.user)
        if user.is_authenticated:
            record_authentication_event(
                event_type=AccountEventType.LOGOUT,
                user=user,
                reason="Encerramento explícito da sessão local.",
            )
        return super().post(request, *args, **kwargs)


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _add_service_error(form: forms.Form, error: ValidationError) -> None:
    if hasattr(error, "message_dict"):
        for field, messages_list in error.message_dict.items():
            target = field if field in form.fields else None
            for message in messages_list:
                form.add_error(target, message)
        return
    for message in error.messages:
        form.add_error(None, message)


@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/home.html")


@login_required
@permission_required("accounts.manage_users")
def user_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    users = User.objects.order_by("username")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    return render(
        request,
        "accounts/user_list.html",
        {"users": users[:200], "query": query},
    )


@login_required
@permission_required("accounts.manage_users")
@require_http_methods(["GET", "POST"])
def user_create(request: HttpRequest) -> HttpResponse:
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = CreateUserService().execute(
                CreateUserCommand(
                    actor=_user(request),
                    username=str(form.cleaned_data["username"]),
                    email=str(form.cleaned_data["email"]),
                    first_name=str(form.cleaned_data["first_name"]),
                    last_name=str(form.cleaned_data["last_name"]),
                    password=str(form.cleaned_data["password1"]),
                    must_change_password=bool(form.cleaned_data["must_change_password"]),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Usuário criado com auditoria registrada.")
            return redirect("accounts:user-detail", user_id=user.pk)
    return render(
        request,
        "accounts/form.html",
        {"form": form, "title": "Criar usuário", "submit_label": "Criar usuário"},
    )


@login_required
@permission_required("accounts.manage_users")
def user_detail(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    assignments = target.role_assignments.select_related("role", "assigned_by").order_by(
        "-is_active",
        "role__code",
        "scope_key",
    )
    return render(
        request,
        "accounts/user_detail.html",
        {"target": target, "assignments": assignments},
    )


@login_required
@permission_required("accounts.manage_users")
@require_http_methods(["GET", "POST"])
def user_update(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    initial = {
        "version": target.version,
        "first_name": target.first_name,
        "last_name": target.last_name,
        "email": target.email,
        "is_active": target.is_active,
    }
    form = UserUpdateForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            target = UpdateUserService().execute(
                UpdateUserCommand(
                    actor=_user(request),
                    user_id=target.pk,
                    expected_version=int(form.cleaned_data["version"]),
                    email=str(form.cleaned_data["email"]),
                    first_name=str(form.cleaned_data["first_name"]),
                    last_name=str(form.cleaned_data["last_name"]),
                    is_active=bool(form.cleaned_data["is_active"]),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Usuário atualizado com auditoria registrada.")
            return redirect("accounts:user-detail", user_id=target.pk)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Editar usuário: {target.username}",
            "submit_label": "Salvar alterações",
        },
    )


@login_required
@permission_required("accounts.manage_users")
@require_http_methods(["GET", "POST"])
def reset_password(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    form = ResetPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ResetPasswordService().execute(
                ResetPasswordCommand(
                    actor=_user(request),
                    user_id=target.pk,
                    password=str(form.cleaned_data["password1"]),
                    must_change_password=bool(form.cleaned_data["must_change_password"]),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Senha temporária redefinida.")
            return redirect("accounts:user-detail", user_id=target.pk)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Redefinir senha: {target.username}",
            "submit_label": "Redefinir senha",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def change_own_password(request: HttpRequest) -> HttpResponse:
    form = ChangeOwnPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = ChangeOwnPasswordService().execute(
                ChangeOwnPasswordCommand(
                    user_id=_user(request).pk,
                    current_password=str(form.cleaned_data["old_password"]),
                    new_password=str(form.cleaned_data["password1"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            update_session_auth_hash(request, user)
            messages.success(request, "Senha alterada.")
            return redirect("accounts:home")
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": "Alterar minha senha",
            "submit_label": "Alterar senha",
        },
    )


@login_required
@permission_required("accounts.manage_roles")
@require_http_methods(["GET", "POST"])
def assign_role(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    form = RoleAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role = cast(Role, form.cleaned_data["role"])
        try:
            AssignRoleService().execute(
                AssignRoleCommand(
                    actor=_user(request),
                    user_id=target.pk,
                    role_id=role.pk,
                    scope_type=ScopeType(str(form.cleaned_data["scope_type"])),
                    company_code=cast(int | None, form.cleaned_data["company_code"]),
                    branch_code=cast(int | None, form.cleaned_data["branch_code"]),
                    valid_from=form.cleaned_data["valid_from"],
                    valid_until=form.cleaned_data["valid_until"],
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Papel atribuído ao usuário.")
            return redirect("accounts:user-detail", user_id=target.pk)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Atribuir papel: {target.username}",
            "submit_label": "Atribuir papel",
        },
    )


@login_required
@permission_required("accounts.manage_roles")
@require_http_methods(["GET", "POST"])
def revoke_role(request: HttpRequest, assignment_id: int) -> HttpResponse:
    assignment = get_object_or_404(
        RoleAssignment.objects.select_related("user", "role"),
        pk=assignment_id,
    )
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            RevokeRoleService().execute(
                RevokeRoleCommand(
                    actor=_user(request),
                    assignment_id=assignment.pk,
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Atribuição de papel revogada.")
            return redirect("accounts:user-detail", user_id=assignment.user_id)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Revogar {assignment.role.code} de {assignment.user.username}",
            "submit_label": "Confirmar revogação",
        },
    )


@login_required
@permission_required("accounts.link_ad_identity")
@require_http_methods(["GET", "POST"])
def link_ad(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    form = AdLinkForm(request.POST or None, initial={"version": target.version})
    if request.method == "POST" and form.is_valid():
        try:
            target = LinkAdIdentityService().execute(
                LinkAdIdentityCommand(
                    actor=_user(request),
                    user_id=target.pk,
                    expected_version=int(form.cleaned_data["version"]),
                    identifier=str(form.cleaned_data["identifier"]),
                    username=str(form.cleaned_data["username"]),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Identidade AD vinculada administrativamente.")
            return redirect("accounts:user-detail", user_id=target.pk)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Vincular identidade AD: {target.username}",
            "submit_label": "Confirmar vínculo",
            "notice": (
                "Este vínculo não ativa autenticação LDAP/AD. A autenticação permanece "
                "local até a homologação do contrato com a Infraestrutura."
            ),
        },
    )


@login_required
@permission_required("accounts.link_ad_identity")
@require_http_methods(["GET", "POST"])
def unlink_ad(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    form = ReasonVersionForm(request.POST or None, initial={"version": target.version})
    if request.method == "POST" and form.is_valid():
        try:
            target = UnlinkAdIdentityService().execute(
                UnlinkAdIdentityCommand(
                    actor=_user(request),
                    user_id=target.pk,
                    expected_version=int(form.cleaned_data["version"]),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Identidade AD desvinculada.")
            return redirect("accounts:user-detail", user_id=target.pk)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Desvincular identidade AD: {target.username}",
            "submit_label": "Confirmar desvínculo",
        },
    )


@login_required
@permission_required("accounts.manage_roles")
def role_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "accounts/role_list.html",
        {"roles": Role.objects.prefetch_related("permissions").order_by("code")},
    )


@login_required
@permission_required("accounts.manage_roles")
@require_http_methods(["GET", "POST"])
def role_create(request: HttpRequest) -> HttpResponse:
    form = RoleForm(request.POST or None, is_create=True)
    if request.method == "POST" and form.is_valid():
        permissions = form.cleaned_data["permissions"]
        try:
            role = CreateRoleService().execute(
                CreateRoleCommand(
                    actor=_user(request),
                    code=str(form.cleaned_data["code"]),
                    name=str(form.cleaned_data["name"]),
                    description=str(form.cleaned_data["description"]),
                    permission_ids=tuple(permission.pk for permission in permissions),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Papel criado.")
            return redirect("accounts:role-update", role_id=role.pk)
    return render(
        request,
        "accounts/form.html",
        {"form": form, "title": "Criar papel", "submit_label": "Criar papel"},
    )


@login_required
@permission_required("accounts.manage_roles")
@require_http_methods(["GET", "POST"])
def role_update(request: HttpRequest, role_id: int) -> HttpResponse:
    role = get_object_or_404(Role.objects.prefetch_related("permissions"), pk=role_id)
    initial = {
        "version": role.version,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "permissions": role.permissions.all(),
    }
    form = RoleForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        permissions = form.cleaned_data["permissions"]
        try:
            role = UpdateRoleService().execute(
                UpdateRoleCommand(
                    actor=_user(request),
                    role_id=role.pk,
                    expected_version=int(form.cleaned_data["version"]),
                    name=str(form.cleaned_data["name"]),
                    description=str(form.cleaned_data["description"]),
                    is_active=bool(form.cleaned_data["is_active"]),
                    permission_ids=tuple(permission.pk for permission in permissions),
                    reason=str(form.cleaned_data["reason"]),
                )
            )
        except ValidationError as exc:
            _add_service_error(form, exc)
        else:
            messages.success(request, "Papel atualizado.")
            return redirect("accounts:role-update", role_id=role.pk)
    return render(
        request,
        "accounts/form.html",
        {
            "form": form,
            "title": f"Editar papel: {role.code}",
            "submit_label": "Salvar papel",
        },
    )


@login_required
@permission_required("accounts.view_account_audit")
def audit_list(request: HttpRequest) -> HttpResponse:
    events = AccountAuditEvent.objects.select_related("actor", "target_user")[:300]
    return render(request, "accounts/audit_list.html", {"events": events})
