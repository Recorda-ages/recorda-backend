# PostgreSQL descartável — PR #135

Validação local realizada em **22/10/2026**, sobre o código da aplicação do commit `069764048fa049a5865ab90cfac65a46605ec410`.

## Resultados

- **7 testes PostgreSQL: passaram, zero skips** (`3.74s`).
- **Suíte completa com os testes PostgreSQL habilitados: 755 passaram, zero skips** (`52.60s`).
- **Cobertura global: 98,46%**. Os demais fixtures continuam usando SQLite, conforme a configuração existente; os sete testes específicos usam PostgreSQL real.
- Um aviso existente do TestClient sobre depreciação de `httpx` no Starlette.

| Teste | Resultado |
| --- | --- |
| Upgrade/downgrade de CONTENT_REMOVED preserva notificações sociais | Passou |
| Trigger impede UPDATE de moderation_action | Passou |
| Trigger impede DELETE de moderation_action | Passou |
| Trigger impede UPDATE em lote de moderation_action | Passou |
| Trigger impede DELETE em lote de moderation_action | Passou |
| Trigger permite INSERT em moderation_action | Passou |
| Follow em andamento é aceito ao tornar a conta pública, com duas sessões e bloqueio real | Passou |

[Saída dos sete testes](postgres-test-output.txt) · [Saída da suíte completa e cobertura](postgres-full-suite-output.txt).

## Isolamento

- Docker com a imagem `postgres:16-alpine`; servidor **PostgreSQL 16.15**, x86_64 Alpine.
- Container exclusivo `recorda-111-postgres-test-20261022`, criado com `--rm` e `--tmpfs /var/lib/postgresql/data:rw`, sem volume persistente.
- Porta vinculada apenas a `127.0.0.1`; banco `test_recorda_111` e usuário `recorda_test`, ambos exclusivos da execução.
- `DATABASE_URL=sqlite://` no processo de testes, separado do destino de `TEST_DATABASE_URL`.
- `TEST_DATABASE_ALLOW_DESTRUCTIVE=1` exclusivamente no processo de testes; a guarda `tests.pg_guard` foi mantida. A fixture recriou somente o schema do banco descartável.
- Nenhum arquivo `.env`, banco de desenvolvimento ou configuração de produção foi alterado.
- Após os testes, a identidade e o rótulo do container foram conferidos; ele foi parado e removido automaticamente, incluindo os dados em tmpfs. Nenhum volume persistente foi criado.

## Reprodução

Execute em PowerShell na raiz do backend, com Docker disponível. As credenciais abaixo são somente um exemplo descartável.

```powershell
docker run --detach --rm --name recorda-111-pg-repro --tmpfs /var/lib/postgresql/data:rw --publish 127.0.0.1::5432 --env POSTGRES_DB=test_recorda_111 --env POSTGRES_USER=recorda_test --env POSTGRES_PASSWORD=recorda111_disposable_only postgres:16-alpine
docker exec recorda-111-pg-repro pg_isready -U recorda_test -d test_recorda_111
# Prossiga somente quando o servidor estiver aceitando conexões.
$binding = docker port recorda-111-pg-repro 5432/tcp
$testPort = [int](($binding -split ':')[-1])
$env:ENVIRONMENT = 'test'
$env:DATABASE_URL = 'sqlite://'
$env:TEST_DATABASE_URL = "postgresql+psycopg://recorda_test:recorda111_disposable_only@127.0.0.1:${testPort}/test_recorda_111"
$env:TEST_DATABASE_ALLOW_DESTRUCTIVE = '1'

.venv/Scripts/python.exe -m pytest tests/test_content_removed_migration.py tests/test_moderation_action_immutability.py tests/test_settings_concurrency.py --no-cov -vv -ra
.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing -ra

docker stop recorda-111-pg-repro
Remove-Item Env:TEST_DATABASE_URL, Env:TEST_DATABASE_ALLOW_DESTRUCTIVE, Env:DATABASE_URL, Env:ENVIRONMENT
```

O workflow atual do GitHub Actions continua sem serviço PostgreSQL e pode exibir os sete skips no CI. A execução local acima fecha essa pendência de validação sem alterar a infraestrutura do pipeline. As capturas do Swagger e do terminal de 21/10 foram preservadas como histórico; os resultados atualizados estão nos logs de 22/10.
