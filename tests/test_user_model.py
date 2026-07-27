import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.django_db
def test_user_is_registered_locally() -> None:
    user = User.objects.create_user(
        username="gestor.teste",
        email="gestor.teste@example.invalid",
        password="a-test-password",
    )

    assert user.email == "gestor.teste@example.invalid"
    assert user.ad_identifier is None
    assert user.check_password("a-test-password")


@pytest.mark.django_db(transaction=True)
def test_ad_identifier_cannot_be_linked_twice() -> None:
    User.objects.create_user(
        username="primeiro.usuario",
        email="primeiro@example.invalid",
        password="a-test-password",
        ad_identifier="immutable-ad-id",
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="segundo.usuario",
            email="segundo@example.invalid",
            password="a-test-password",
            ad_identifier="immutable-ad-id",
        )
