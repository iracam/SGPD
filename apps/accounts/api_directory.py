"""Administrative, read-only directory discovery and explicit provisioning."""

from __future__ import annotations

from typing import Any, cast

from django.db.models import Q
from rest_framework.request import Request
from rest_framework.response import Response

from apps.integrations.active_directory.client import ActiveDirectoryClient
from apps.integrations.active_directory.dto import DirectoryGroup, DirectoryUser
from apps.integrations.active_directory.exceptions import (
    DirectoryConfigurationError,
    DirectoryContractError,
    DirectoryIdentityNotFoundError,
    DirectoryUnavailableError,
)
from config.api import api_error

from .api_accounts import AccountsAPIView, user_detail_payload
from .models import User
from .serializers import DirectoryUserCreateSerializer
from .services import (
    LINK_AD_IDENTITY_PERMISSION,
    CreateUserFromDirectoryCommand,
    CreateUserFromDirectoryService,
)


def _directory_error(exc: Exception) -> Response:
    if isinstance(exc, DirectoryConfigurationError):
        return api_error(
            code="directory_not_configured",
            message=str(exc),
            status_code=503,
        )
    if isinstance(exc, DirectoryUnavailableError):
        return api_error(
            code="directory_unavailable",
            message="O Active Directory está indisponível. Tente novamente mais tarde.",
            status_code=503,
        )
    if isinstance(exc, DirectoryIdentityNotFoundError):
        return api_error(
            code="directory_identity_not_found",
            message=str(exc),
            status_code=404,
        )
    return api_error(
        code="directory_contract_error",
        message=str(exc),
        status_code=502,
    )


def _directory_user_payload(
    identity: DirectoryUser,
    local_users: list[User],
) -> dict[str, Any]:
    linked = next(
        (user for user in local_users if user.ad_identifier == identity.identifier),
        None,
    )
    username_conflict = next(
        (
            user
            for user in local_users
            if user.username.casefold() == identity.username.casefold()
            and user.ad_identifier != identity.identifier
        ),
        None,
    )
    email_conflict = next(
        (
            user
            for user in local_users
            if identity.email
            and user.email.casefold() == identity.email.casefold()
            and user.ad_identifier != identity.identifier
        ),
        None,
    )
    return {
        "identifier": identity.identifier,
        "username": identity.username,
        "user_principal_name": identity.user_principal_name,
        "first_name": identity.first_name,
        "last_name": identity.last_name,
        "display_name": identity.display_name,
        "email": identity.email,
        "distinguished_name": identity.distinguished_name,
        "can_import": (
            identity.can_import
            and linked is None
            and username_conflict is None
            and email_conflict is None
        ),
        "missing_import_fields": list(identity.missing_import_fields),
        "local_user": (
            {"id": linked.pk, "username": linked.username} if linked is not None else None
        ),
        "username_conflict": (
            {"id": username_conflict.pk, "username": username_conflict.username}
            if username_conflict is not None
            else None
        ),
        "email_conflict": (
            {"id": email_conflict.pk, "username": email_conflict.username}
            if email_conflict is not None
            else None
        ),
    }


def _directory_group_payload(group: DirectoryGroup) -> dict[str, Any]:
    return {
        "distinguished_name": group.distinguished_name,
        "name": group.name,
        "account_name": group.account_name,
        "description": group.description,
    }


class DirectoryStatusView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def get(self, request: Request) -> Response:
        del request
        return Response(ActiveDirectoryClient().status())


class DirectoryUserSearchView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "")
        if len(query.strip()) < 2:
            return api_error(
                code="validation_error",
                message="Os dados informados são inválidos.",
                status_code=400,
                details={"q": ["Informe ao menos dois caracteres para a busca."]},
            )
        if len(query) > 100:
            return api_error(
                code="validation_error",
                message="Os dados informados são inválidos.",
                status_code=400,
                details={"q": ["A busca deve ter no máximo 100 caracteres."]},
            )
        try:
            limit = int(request.query_params.get("limit", 50))
        except ValueError:
            limit = 50
        client = ActiveDirectoryClient()
        try:
            identities = client.search_users(
                query,
                limit=limit,
            )
        except (
            DirectoryConfigurationError,
            DirectoryUnavailableError,
            DirectoryContractError,
        ) as exc:
            return _directory_error(exc)

        identifiers = [item.identifier for item in identities]
        usernames = [item.username for item in identities]
        emails = [item.email for item in identities if item.email]
        local_users = list(
            User.objects.filter(
                Q(ad_identifier__in=identifiers) | Q(username__in=usernames) | Q(email__in=emails)
            ).order_by("pk")
        )
        return Response(
            {
                "limit": min(max(limit, 1), client.config.result_limit),
                "results": [
                    _directory_user_payload(identity, local_users) for identity in identities
                ],
            }
        )


class DirectoryGroupSearchView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "")
        if len(query.strip()) < 2:
            return api_error(
                code="validation_error",
                message="Os dados informados são inválidos.",
                status_code=400,
                details={"q": ["Informe ao menos dois caracteres para a busca."]},
            )
        if len(query) > 100:
            return api_error(
                code="validation_error",
                message="Os dados informados são inválidos.",
                status_code=400,
                details={"q": ["A busca deve ter no máximo 100 caracteres."]},
            )
        try:
            limit = int(request.query_params.get("limit", 50))
        except ValueError:
            limit = 50
        client = ActiveDirectoryClient()
        try:
            groups = client.search_groups(query, limit=limit)
        except (
            DirectoryConfigurationError,
            DirectoryUnavailableError,
            DirectoryContractError,
        ) as exc:
            return _directory_error(exc)
        return Response(
            {
                "limit": min(max(limit, 1), client.config.result_limit),
                "results": [_directory_group_payload(group) for group in groups],
            }
        )


class DirectoryUserCreateView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def post(self, request: Request) -> Response:
        serializer = DirectoryUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            user = CreateUserFromDirectoryService().execute(
                CreateUserFromDirectoryCommand(
                    actor=self.actor(request),
                    identifier=data["identifier"],
                )
            )
        except (
            DirectoryConfigurationError,
            DirectoryUnavailableError,
            DirectoryContractError,
            DirectoryIdentityNotFoundError,
        ) as exc:
            return _directory_error(exc)
        return Response(user_detail_payload(user), status=201)
