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


def test_empty_oracle_character_value_is_not_an_ad_link() -> None:
    user = User(
        username="usuario.oracle",
        email="usuario.oracle@example.invalid",
        first_name="Usuário",
        last_name="Oracle",
        ad_identifier="",
        ad_username="",
    )

    assert not user.has_ad_link
    user.clean()
    assert user.ad_identifier is None
    assert user.ad_username is None


@pytest.mark.django_db(transaction=True)
def test_partial_ad_link_is_rejected_by_database_constraint() -> None:
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="usuario.parcial",
            email="usuario.parcial@example.invalid",
            password="a-test-password",
            ad_identifier="immutable-ad-id",
        )
