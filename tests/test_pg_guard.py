"""Salvaguarda que impede a fixture pg_db de recriar o schema do banco errado.

Testes puros sobre a função de guarda: não abrem conexão e rodam no CI.
"""

import pytest

from tests.pg_guard import UnsafeTestDatabaseError, assert_disposable_database

APP_URL = "postgresql+psycopg://postgres:postgres@db:5432/recorda"
SAFE_URL = "postgresql+psycopg://postgres:postgres@localhost:15432/test_recorda_audit"


def guard(url: str, *, app_url: str = APP_URL, allow: str | None = "1") -> None:
    assert_disposable_database(url, app_url=app_url, allow_destructive=allow)


def test_a_properly_named_test_database_with_the_flag_is_accepted():
    guard(SAFE_URL)


@pytest.mark.parametrize(
    "database",
    ["test_recorda_audit", "test_x", "recorda_test", "auditoria_test"],
)
def test_both_accepted_name_shapes(database: str):
    guard(f"postgresql+psycopg://postgres:postgres@localhost:15432/{database}")


# --------------------------------------------------------------------------- #
# Condição 1 — nome do database
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "database",
    [
        "recorda",  # o banco de desenvolvimento
        "postgres",  # o default da aplicação
        "recorda_mig_check",  # descartável, mas sem nome de teste
        "recorda_test_fixtures",  # 'test' no meio não basta
        "testing",  # não é 'test_' nem '_test'
        "",  # sem database na URL
    ],
)
def test_database_name_outside_the_pattern_is_refused(database: str):
    with pytest.raises(UnsafeTestDatabaseError, match="banco de teste"):
        guard(f"postgresql+psycopg://postgres:postgres@localhost:15432/{database}")


def test_the_word_test_in_the_host_does_not_satisfy_the_pattern():
    """Só o componente de database é inspecionado, nunca a URL inteira."""
    with pytest.raises(UnsafeTestDatabaseError, match="banco de teste"):
        guard("postgresql+psycopg://postgres:postgres@test-db.interno:5432/recorda")


def test_the_word_test_in_the_username_does_not_satisfy_the_pattern():
    with pytest.raises(UnsafeTestDatabaseError, match="banco de teste"):
        guard("postgresql+psycopg://tester:tester@localhost:5432/recorda")


# --------------------------------------------------------------------------- #
# Condição 2 — confirmação explícita
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("allow", [None, "", "0", "true", "yes", "1 "])
def test_missing_or_wrong_destructive_flag_is_refused(allow: str | None):
    with pytest.raises(UnsafeTestDatabaseError, match="ALLOW_DESTRUCTIVE"):
        guard(SAFE_URL, allow=allow)


# --------------------------------------------------------------------------- #
# Condição 3 — não pode ser o banco da aplicação
# --------------------------------------------------------------------------- #


def test_the_application_database_is_refused_even_if_well_named():
    """Nome de teste e flag presentes não liberam o banco configurado."""
    app_url = "postgresql+psycopg://postgres:postgres@db:5432/test_recorda_audit"

    with pytest.raises(UnsafeTestDatabaseError, match="coincide"):
        guard(
            "postgresql+psycopg://postgres:postgres@db:5432/test_recorda_audit",
            app_url=app_url,
        )


def test_same_database_name_on_another_host_is_accepted():
    guard(SAFE_URL, app_url="postgresql+psycopg://u:p@db:5432/test_recorda_audit")


# --------------------------------------------------------------------------- #
# Mensagem de erro
# --------------------------------------------------------------------------- #


def test_every_failed_condition_is_reported_at_once():
    with pytest.raises(UnsafeTestDatabaseError) as error:
        guard(APP_URL, allow=None)

    message = str(error.value)
    assert "banco de teste" in message
    assert "ALLOW_DESTRUCTIVE" in message
    assert "coincide" in message
    assert "DROP SCHEMA public CASCADE" in message


def test_the_error_message_documents_the_expected_pattern():
    with pytest.raises(UnsafeTestDatabaseError) as error:
        guard(APP_URL)

    message = str(error.value)
    assert "test_" in message and "_test" in message
    assert "test_recorda_audit" in message


def test_the_password_is_not_leaked_in_the_error_message():
    with pytest.raises(UnsafeTestDatabaseError) as error:
        guard("postgresql+psycopg://postgres:supersecret@db:5432/recorda")

    assert "supersecret" not in str(error.value)
