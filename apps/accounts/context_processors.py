"""Navigation flags derived from the same authorization service used by views."""

from django.http import HttpRequest

from apps.integrations.senior.permissions import SENIOR_REFERENCE_PERMISSION

from .authorization import allowed_company_codes, has_permission
from .models import User


def account_permissions(request: HttpRequest) -> dict[str, bool]:
    user = request.user
    if not isinstance(user, User) or not user.is_authenticated:
        return {}
    allowed_senior_companies = allowed_company_codes(
        user,
        SENIOR_REFERENCE_PERMISSION,
    )
    return {
        "can_manage_users": has_permission(user, "accounts.manage_users"),
        "can_manage_roles": has_permission(user, "accounts.manage_roles"),
        "can_link_ad": has_permission(user, "accounts.link_ad_identity"),
        "can_view_account_audit": has_permission(user, "accounts.view_account_audit"),
        "can_query_senior_references": allowed_senior_companies != set(),
    }
