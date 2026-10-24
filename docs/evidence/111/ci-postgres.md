# PostgreSQL no CI e atualização da base — 23/10/2026

O job `test-unit` de `.github/workflows/ci.yml` agora sobe um serviço `postgres:16-alpine` exclusivo do runner e espera `pg_isready` antes de executar o pytest. O banco se chama `test_recorda_ci`; as credenciais declaradas no YAML são exclusivas desse serviço efêmero.

O job configura `TEST_DATABASE_URL` e `TEST_DATABASE_ALLOW_DESTRUCTIVE=1`, mantendo `DATABASE_URL=sqlite://` para separar o destino descartável do banco da aplicação. As três verificações de `tests.pg_guard` continuam ativas. A suíte roda com cobertura mínima de 80% e `-ra`, mostrando os motivos de qualquer skip. Os demais fixtures permanecem em SQLite.

Os sete testes específicos cobrem a migration de notificações, cinco comportamentos do trigger append-only de auditoria e a concorrência entre follow e publicação da conta. Eles passam a fazer parte da execução normal do pipeline, sem uma segunda execução duplicada.

## Rebase

A branch foi rebased sobre `origin/dev` no commit `7fe29d10db7bbc198dd59cf0d22160d8cd0fc0f0`, incorporando 18 commits novos da base. O conflito em `app/api/routes/user.py` foi resolvido preservando `ProfileRead`/`profile_service` e unificando o PATCH de idioma da #112 com o PATCH de privacidade da #111.

Há uma única rota de escrita de configurações. O schema aceita `language` em `pt-BR`, `en` ou `es`, como já fazia a base atualizada; idioma, privacidade e aceites são persistidos na mesma transação. O campo adicional `accepted_requests` permanece na resposta. Foram removidos o writer e os schemas duplicados que poderiam contornar o aceite atômico.

Os 48 testes de idioma e configurações foram executados durante a resolução. As falhas de persistência/validação de idioma foram observadas antes da unificação e desapareceram após a correção. O teste de rollback também verifica que uma mudança conjunta de idioma é desfeita se o aceite falhar.

## Evidências

- A execução local de 23/10 passou com **811 testes, zero skips e 98,32% de cobertura**, incluindo os sete testes PostgreSQL. O PostgreSQL 16.15 rodou em um container exclusivo com armazenamento temporário, sem usar bancos da aplicação.
- O container local foi parado e removido após a validação.
- [Execução local completa após o rebase, com PostgreSQL habilitado](ci-postgres-local-output.txt).
- A execução remota e seus resultados ficam nos checks do [PR #135](https://github.com/Recorda-ages/recorda-backend/pull/135).

Configuração baseada no padrão oficial para [serviços PostgreSQL em jobs executados diretamente no runner](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers#running-jobs-directly-on-the-runner-machine).
