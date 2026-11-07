# Issue #145 — Memórias diárias

Implementado `GET /api/v1/users/me/calendar/day?date=YYYY-MM-DD` na branch local `feat/145-daily-calendar-memories`, criada de `origin/dev`.

## Comportamento

- Autenticação Bearer obrigatória; o autor é sempre o usuário autenticado.
- Dia civil em `America/Sao_Paulo`, delimitado em UTC por `local_day_bounds()` e consultado como `[start, end)`.
- Somente Recordas vivas do próprio usuário, em `created_at ASC, recorda_id ASC`.
- `DailyMemoriesResponse` contém `date`, `total_count`, `memories`, `previous_date_with_memories` e `next_date_with_memories`.
- Cada memória contém o contrato existente de `RecordaDetail`, além de `comments_count` e `formatted_time` (`HH:MM` local). `created_at` preserva o instante com fuso.
- `song_preview_url` é o caminho `/api/v1/music/tracks/{id}/preview`, ou `null` quando não há prévia; não há consulta ao Deezer ao montar o calendário.
- Curtidas seguem a contagem existente; `is_liked` informa a curtida do próprio usuário. Comentários excluídos e de contas suspensas ou excluídas não entram na contagem.
- A navegação encontra os dias vivos mais próximos, inclusive em outros meses/anos. Em dia vazio, retorna 200 com lista vazia, total zero e ponteiros calculados normalmente.
- Parâmetro ausente, formato diferente de `YYYY-MM-DD`, data inexistente, timestamp e número de época retornam 422 no envelope `VALIDATION_ERROR`, com campo `date`. `9999-12-31` também retorna 422: o helper precisa calcular o dia seguinte.

As consultas ficam nos repositórios e a montagem dos DTOs no serviço. A lista reaproveita a consulta do calendário mensal; navegação usa duas agregações escalares na mesma consulta. Curtidas e comentários são agrupados em lote, sem consultas por memória.

## Validação em 07/11/2026

- Suíte completa: **1.003 testes passaram**, incluindo PostgreSQL 16 descartável com migrations.
- Os mesmos 11 cenários diários de serviço foram exercitados em SQLite e PostgreSQL: lista vazia, limites locais e exclusões, navegação, engajamento, desempate de timestamps e dia de 25 horas.
- Cobertura global: **98,74%**. Rota, schemas e serviço de calendário: **100%** de linhas cobertas.
- `ruff check .`, `ruff format --check .` e `git diff --check`: passaram.
- Smoke HTTP com dados sintéticos: 200 com múltiplas memórias, 200 em dia vazio com navegação, 422 em data impossível e 401 sem autenticação.
- Medição manual do serviço: **5 consultas SQL tanto para 1 quanto para 20 memórias**, incluindo autoria e engajamento. Dia vazio dispensa consultas de autoria e engajamento.

Comando da suíte completa (o ambiente de testes sobrescreve um `DEBUG=release` herdado do host):

```bash
env -u TEST_DATABASE_URL DEBUG=false ENVIRONMENT=test DATABASE_URL=sqlite:// .venv/bin/pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage-unit.xml --cov-fail-under=80 -ra tests/
```

Sem `TEST_DATABASE_URL`, a fixture existente provisiona seu próprio PostgreSQL descartável no Docker. Não foi usado banco da aplicação.

Os logs de execução e os relatórios de cobertura devem acompanhar a descrição do PR ou ser publicados como artefatos da CI. Não são versionados como arquivos `.txt` na árvore da branch.

- [Respostas HTTP e medição de consultas](evidence/145/http-smoke.json).

## Contrato do cliente

O tipo provisório do frontend também declara `comments` e `thumbnail_url`. Esses campos não fazem parte desta resposta: a issue exige a contagem de comentários, e o visualizador consultado não usa esses dois campos. O horário `formatted_time`, que o visualizador usa, é retornado. Antes de integrar tipos gerados ou ampliar o visualizador, alinhar a definição provisória ao OpenAPI entregue pelo backend. Não houve alteração no repositório frontend.

Nenhuma migration ou dependência foi adicionada. As evidências locais preexistentes da #147 foram preservadas.
