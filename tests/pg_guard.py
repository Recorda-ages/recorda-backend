"""Salvaguarda da fixture `pg_db`, que recria o schema do banco de destino.

A fixture executa `DROP SCHEMA public CASCADE`. Para que isso nunca atinja o
banco de desenvolvimento, três condições têm de valer ao mesmo tempo (defesa
em profundidade):

1. o nome do database casa com um padrão conservador de banco de teste;
2. `TEST_DATABASE_ALLOW_DESTRUCTIVE=1` está definida;
3. o destino não coincide com o banco configurado pela aplicação.

Qualquer falha levanta `UnsafeTestDatabaseError` **antes** do `DROP SCHEMA`.
Não há skip: configuração destrutiva insegura é erro, não motivo para
silenciar o teste.
"""

import re

from sqlalchemy.engine import make_url

#: Conservador de propósito: o nome do database precisa começar com `test_`
#: ou terminar com `_test`. Só o componente de database é testado — nunca a
#: URL inteira, para que um host `test-db.interno` ou um usuário `tester`
#: não passem por engano.
TEST_DB_NAME_PATTERN = re.compile(r"^test_|_test$")

ALLOW_DESTRUCTIVE_ENV = "TEST_DATABASE_ALLOW_DESTRUCTIVE"


class UnsafeTestDatabaseError(RuntimeError):
    """O destino de `TEST_DATABASE_URL` não é reconhecido como descartável."""


def assert_disposable_database(
    url: str,
    *,
    app_url: str,
    allow_destructive: str | None,
) -> None:
    """Valida que `url` aponta para um banco de teste descartável."""
    target = make_url(url)
    database = target.database or ""
    problems = []

    if not TEST_DB_NAME_PATTERN.search(database):
        problems.append(
            f"o database {database!r} não é reconhecido como banco de teste: "
            f"o nome precisa começar com 'test_' ou terminar com '_test' "
            f"(ex.: 'test_recorda_audit')"
        )

    if allow_destructive != "1":
        problems.append(
            f"{ALLOW_DESTRUCTIVE_ENV} não está definida como '1'; a fixture "
            f"recria o schema do banco e exige confirmação explícita"
        )

    application = make_url(app_url)
    if (target.host, target.port, database) == (
        application.host,
        application.port,
        application.database,
    ):
        problems.append(
            "o destino coincide com o banco configurado pela aplicação "
            "(mesmo host, porta e database)"
        )

    if problems:
        raise UnsafeTestDatabaseError(
            "Recusando executar DROP SCHEMA public CASCADE em "
            f"{target.render_as_string(hide_password=True)}:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
        )
