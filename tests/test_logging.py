import json
import logging

from config.logging import JsonFormatter


def test_json_formatter_projects_safe_role_assignment_metadata() -> None:
    record = logging.LogRecord(
        name="apps.accounts.api_accounts",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="account_role_assignment_completed",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(
        {
            "actor_id": 24,
            "target_user_id": 25,
            "role_id": 11,
            "assignment_id": 22,
            "scope_key": "*",
            "outcome": "completed",
            "email": "nao-projetar@example.invalid",
        }
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "account_role_assignment_completed"
    assert payload["actor_id"] == 24
    assert payload["target_user_id"] == 25
    assert payload["role_id"] == 11
    assert payload["assignment_id"] == 22
    assert payload["scope_key"] == "*"
    assert payload["outcome"] == "completed"
    assert "email" not in payload
