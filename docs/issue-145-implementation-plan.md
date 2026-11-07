# Plano de implementação — Issue #145

Data: 07/11/2026. Status: backend implementado e validado. Este documento preserva o plano aprovado; resultados e contrato entregue em [issue-145.md](issue-145.md).

Issue: [T-E7.US37.BE.02 — Detalhe diário com carrossel cronológico e navegação temporal](https://github.com/Recorda-ages/recorda-backend/issues/145).

Branch local criada: `feat/145-daily-calendar-memories`, a partir de `origin/dev` em `4a55515d025c5c0b517efdb39ede274d4f9f7272`. A revisão foi conferida com a branch remota do GitHub. Essa base já contém o calendário mensal da #144. Os commits da branch anterior, relativos à #147, não fazem parte desta branch; as evidências locais não versionadas de #147 foram preservadas.

## 1. Objetivo e escopo

Entregar `GET /api/v1/users/me/calendar/day?date=YYYY-MM-DD`, autenticado, retornando todas as Recordas vivas do usuário no dia civil de `America/Sao_Paulo`, em ordem cronológica, com prévias musicais pelo proxy, contagens de engajamento e datas vizinhas com memórias.

Dia vazio retorna 200 com lista vazia e navegação calculada normalmente. As datas vizinhas podem estar em outros meses e anos. Recordas excluídas pelo autor ou pela moderação não participam da lista nem da navegação.

Não há necessidade identificada de migrations, dependências novas, cache, paginação ou mudanças no armazenamento de mídia. A implementação do carrossel visual pertence ao frontend; esta task fornece seus dados.

## 2. Orientações aplicadas e estado atual

Referências locais consultadas:

- `../.agents/skills/fastapi-python/SKILL.md`: funções tipadas, validação com Pydantic v2, injeção de dependências e rotas pequenas.
- `../.agents/skills/codebase-design/SKILL.md`: concentrar a lógica atrás de uma interface pequena e aceitar dependências.
- `../.agents/skills/tdd/SKILL.md`, `tests.md` e `mocking.md`: ciclos verticais de teste falhando → implementação mínima, verificando comportamento pela interface pública e usando banco de teste real.
- `CONTRIBUTING.md`: branch em inglês criada de `dev`, arquitetura em camadas, Ruff, Pytest e cobertura mínima de 80%.
- `docs/adr/0001-alinhamento-ao-diagrama-do-banco.md`: UUIDs portáveis e filtros de soft delete nos repositórios.

O backend usa SQLAlchemy `Session` síncrona. Manter `def` e as dependências atuais, sem misturar I/O síncrono com uma rota `async def` ou migrar a infraestrutura nesta task.

Reutilizações disponíveis:

- `app/core/time.py`: `local_day_bounds()` fornece `[start, end)` em UTC respeitando o fuso e seu histórico; `to_local()` converte o instante para São Paulo.
- `recorda_repository.list_by_user_between()`: já filtra autor e `deleted_at IS NULL`, inclui o início, exclui o fim e ordena por `created_at ASC, recorda_id ASC`.
- `calendar_service._local_day()`: já normaliza timestamps sem fuso devolvidos pelo SQLite como UTC antes de obter a data local.
- `public_preview_url()`: devolve o caminho do proxy ou `None` se a faixa não tiver prévia disponível.
- `RecordaDetail` e `RecordaAuthor`: contrato existente para mídia, música, autoria e curtidas.
- `tests/conftest.py`: SQLite real e cliente HTTP com dependências substituídas; `pg_db` oferece PostgreSQL descartável com migrations.

Embora a issue cite consultas auxiliares em `calendar_service.py`, o SQL novo ficará nos repositórios para respeitar `Route → Service → Repository → DB`.

## 3. Contrato proposto

Adicionar em `app/schemas/calendar.py`:

### `DayRecordaDetail`

Estender `RecordaDetail`, preservando seus campos: `recorda_id`, `author`, `media_url`, `media_type`, `description`, dados musicais incluindo `deezer_track_id` e `song_genre_name`, `created_at`, `is_liked` e `likes_count`.

Acrescentar:

- `comments_count: int`, não negativo, contando comentários visíveis.
- `formatted_time: str`, no formato `HH:MM` em `America/Sao_Paulo`, necessário ao visualizador existente.

`created_at` continua sendo um instante ISO 8601 com fuso; normalizar timestamps ingênuos do SQLite para UTC antes de serializar. Não converter o instante em uma string de horário local sem offset.

### `DailyMemoriesResponse`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `date` | `datetime.date` | Data solicitada; JSON `YYYY-MM-DD` |
| `total_count` | `int >= 0` | Quantidade de itens em `memories` |
| `memories` | `list[DayRecordaDetail]` | Ordem `created_at ASC, recorda_id ASC` |
| `previous_date_with_memories` | `datetime.date \| None` | Dia local mais próximo estritamente anterior com Recorda viva |
| `next_date_with_memories` | `datetime.date \| None` | Dia local mais próximo estritamente posterior com Recorda viva |

Exemplo de dia vazio entre duas datas ativas:

```json
{
  "date": "2026-11-07",
  "total_count": 0,
  "memories": [],
  "previous_date_with_memories": "2026-10-30",
  "next_date_with_memories": "2026-11-10"
}
```

### Compatibilidade com o frontend

`../recorda-frontend/src/features/memories-calendar/types.ts` já define esse envelope e marca `DayRecordaDetail` como provisório. O visualizador consome `formatted_time`, mídia e música; seu tipo também exige `thumbnail_url` e `comments`, que não constam na issue e não são usados pelo visualizador consultado.

Proposta: fornecer os campos de detalhe, horário e contagens acima e alinhar os dois campos provisórios no frontend antes da integração. Não devolver `comments: []` para Recordas com comentários nem inventar uma miniatura de vídeo. Se a lista de comentários ou uma miniatura dedicada for confirmada como requisito, tratar explicitamente o contrato e o carregamento correspondente, sem consultas por item. Alterações no frontend não integram este plano de backend.

## 4. Implementação em etapas

### Etapa 1 — Schemas e validação de entrada

1. Criar os dois DTOs e suas descrições para OpenAPI.
2. Definir a conversão do parâmetro público `date` para `datetime.date`, exigindo exatamente `YYYY-MM-DD`, além de uma data existente. Usar validação Pydantic na entrada e preservar o envelope de erros do projeto.
3. Retornar 422 para parâmetro ausente, vazio, data impossível, formato incorreto, timestamp ou número de época. Não depender apenas da coerção permissiva de `date`.
4. Tratar o limite superior não suportado por `local_day_bounds()` — `9999-12-31` exige calcular um dia seguinte inexistente — com erro de validação, evitando 500. Não copiar silenciosamente a restrição de anos do calendário mensal, que não foi exigida para esta rota.

### Etapa 2 — Acesso aos dados sem N+1

1. Reutilizar `list_by_user_between(db, user_id, start, end)` para a lista diária.
2. Adicionar em `recorda_repository.py` a consulta dos instantes vizinhos: `MAX(created_at)` com `created_at < start` e `MIN(created_at)` com `created_at >= end`, sempre para o mesmo autor e com `only_live()`. Pode ser uma consulta com duas subconsultas escalares, sem carregar o histórico inteiro.
3. Adicionar em `recorda_like_repository.py` uma leitura em lote dos IDs do dia, com `likes_count` e `is_liked` pelo próprio usuário. Manter a semântica existente das curtidas: contar as linhas presentes, pois a tabela não tem soft delete. Não introduzir filtro novo de status do autor da curtida só neste endpoint.
4. Adicionar em `comment_repository.py` contagens agrupadas pelos IDs do dia, com `RecordaComment.deleted_at IS NULL` e autores ativos/não excluídos, reproduzindo a visibilidade de `list_for_recorda()`.
5. Para dia vazio, dispensar as consultas de engajamento; ainda consultar os vizinhos. Para posts sem interações, retornar zero e `is_liked=false`.

O número de consultas de domínio deve permanecer limitado independentemente do número de memórias: lista diária, vizinhos, curtidas em lote e comentários em lote. O autor é carregado uma única vez usando `user_repository.get_by_id()`, com aproveitamento da sessão quando já resolvido pela autenticação. Usar agregações separadas evita multiplicar curtidas pelo número de comentários em um JOIN.

Manter predicados de intervalo sobre `created_at`, aproveitando `ix_recorda_user_id_created_at`; não aplicar funções de data/fuso à coluna no filtro e não fazer consultas para cada dia sem publicação.

### Etapa 3 — Orquestração diária

Adicionar uma função pública tipada em `calendar_service.py`, proposta:

```python
def get_daily_memories(
    db: Session, user_id: UUID, target_date: date
) -> DailyMemoriesResponse: ...
```

Fluxo:

1. Obter `start, end = local_day_bounds(target_date)`.
2. Buscar Recordas do intervalo e instantes vizinhos nos repositórios.
3. Carregar autoria uma vez e engajamento em lote.
4. Montar cada `DayRecordaDetail`, chamando `public_preview_url(recorda.deezer_track_id, recorda.song_preview_url)`; nenhuma chamada ao Deezer é necessária nessa leitura.
5. Calcular `formatted_time` e converter os instantes vizinhos em datas locais com a normalização UTC existente. Nunca usar a data UTC diretamente como ponteiro.
6. Retornar o DTO com `total_count=len(memories)` e os ponteiros, inclusive quando a lista estiver vazia.

Não chamar `get_by_id_for_viewer()` em um loop: ele repete consultas de autoria e curtidas para cada Recorda.

### Etapa 4 — Rota HTTP

Adicionar `@router.get("/day", response_model=DailyMemoriesResponse)` em `app/api/routes/calendar.py`, com retorno tipado, `get_current_user` e `get_db`, delegando ao módulo diário.

O autor vem exclusivamente de `current_user.user_id`; não receber `user_id` do cliente. O router de calendário já está registrado em `app/main.py` sob `/api/v1`, portanto não criar outro registro.

Documentar 200, dia vazio e validação 422; manter segurança Bearer e tag `calendar`. Atualizar a tabela de endpoints em `README.md`.

## 5. Estratégia de testes

Interfaces propostas: `get_daily_memories()` para regras de negócio e a rota HTTP para autenticação, validação e serialização. São extensões das interfaces já usadas em `tests/test_calendar_service.py` e `tests/test_calendar_routes.py`.

As interfaces de teste foram incluídas neste plano e aprovadas pelo usuário antes da implementação, conforme a orientação local de TDD. Trabalhar em ciclos verticais: um cenário falhando, implementação suficiente para passá-lo, próximo cenário. Usar as factories e o banco real das fixtures; evitar mocks de módulos internos e testes de helpers privados.

| Grupo | Cenários e resultados esperados |
| --- | --- |
| Lista diária | Um e vários posts, inserção fora de ordem, fotos e vídeos; resultado cronológico; desempate estável por UUID; `total_count` correto |
| Isolamento | Posts de outros autores e posts excluídos, inclusive pela moderação, não aparecem; também não criam datas de navegação |
| Intervalo local | Para 07/11/2026: incluir `2026-11-07T03:00:00Z`, incluir `2026-11-08T02:59:59Z`, excluir o instante anterior ao início e `2026-11-08T03:00:00Z`; conferir `formatted_time` |
| Fusos históricos | Dia de transição de horário de verão; respeitar os limites do helper, sem assumir sempre 24 horas ou offset fixo de três horas |
| Navegação | Vizinhos mais próximos com lacunas, múltiplos posts no mesmo dia, troca de mês/ano, dias anteriores/posteriores sem posts vivos e eventos próximos da meia-noite UTC |
| Ausências | Sem histórico: ambos os ponteiros `null`; só anterior; só posterior; dia vazio entre dois dias ativos |
| Música | URL externa armazenada vira `/api/v1/music/tracks/{id}/preview`; prévia ausente vira `null`; não expor URL temporária do Deezer |
| Engajamento | Zero e várias curtidas, curtida própria presente/ausente, comentários excluídos e de contas suspensas/excluídas ignorados; combinar várias curtidas e comentários para detectar contagem multiplicada |
| HTTP | 200 e envelope completo; 401 sem token; 422 com envelope `VALIDATION_ERROR` e campo `date` para ausências e formatos inválidos; datas serializadas corretamente |
| OpenAPI/regressão | Schema `DailyMemoriesResponse`, Bearer e tag; calendário mensal continua passando |

Usar também PostgreSQL descartável para validar intervalos, timestamps e agregações com as fixtures existentes. Não executar a fixture destrutiva contra banco de desenvolvimento ou produção.

## 6. Arquivos previstos

| Arquivo | Alteração |
| --- | --- |
| `app/schemas/calendar.py` | DTOs diários e contrato de validação de data, se necessário |
| `app/services/calendar_service.py` | Orquestração diária, apresentação do horário e ponteiros locais |
| `app/api/routes/calendar.py` | Rota `/day` e validação do parâmetro |
| `app/repositories/recorda_repository.py` | Instantes vizinhos por autor, ignorando exclusões |
| `app/repositories/recorda_like_repository.py` | Contagens e estado de curtida em lote |
| `app/repositories/comment_repository.py` | Contagens de comentários visíveis em lote |
| `tests/test_calendar_service.py` | Cenários de negócio diários e regressão mensal |
| `tests/test_calendar_routes.py` | Contrato HTTP diário, validação e OpenAPI |
| `README.md` | Documentação do endpoint |

## 7. Validação e conclusão da implementação

Rodar durante os ciclos os testes focados, sem aplicar o limite global de cobertura a uma execução parcial:

```bash
pytest --no-cov tests/test_calendar_service.py tests/test_calendar_routes.py tests/test_time.py tests/test_music_preview.py
```

Ao concluir, executar os checks exigidos pelo repositório:

```bash
ruff check .
ruff format --check .
pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage-unit.xml --cov-fail-under=80 -ra tests/
```

Além do limite global da CI, conferir que o código novo tem cobertura de pelo menos 80%. Registrar evidências HTTP de dia com múltiplos posts, dia vazio, navegação e data inválida, além do relatório de cobertura, em `docs/evidence/145/`.

Antes do PR da implementação, sincronizar com `origin/dev` por rebase, repetir os checks afetados e apontar o PR para `dev`, com Conventional Commit, vínculo à #145 e evidências conforme `CONTRIBUTING.md`.

A entrega do backend foi validada com os critérios da issue e a regressão do calendário mensal. O alinhamento dos campos provisórios do frontend continua sendo uma observação de integração fora do escopo deste repositório. A branch é local; publicação e abertura de PR não fizeram parte desta execução.
