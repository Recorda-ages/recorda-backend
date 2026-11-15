# Alinhamento do schema ao diagrama oficial do banco

O schema provisório (`users`, `recordas`, `music_preferences`, com PK `int`, `recordas.data` em texto `dd/mm/YYYY` e `DELETE` físico) foi substituído pelas tabelas do diagrama oficial (wiki AGES → *Banco de Dados*) que o código já usa: `app_user`, `recorda`, `genre`, `user_favorite_genre` e `user_favorite_artist`. As outras oito tabelas do diagrama ficam para as issues #16–#19. O schema passou a ser versionado com Alembic (issue #15). A migration `0002_diagram_schema` recria as tabelas em vez de convertê-las, porque não há conversão confiável de `int` para `UUID` nem de `dd/mm/YYYY` para `TIMESTAMPTZ`, e os dados de desenvolvimento são descartáveis. Esta mudança substitui o PR #35, que ficou sem a FK para `app_user` e usava `postgresql.UUID`, tipo que não compila no SQLite dos testes.

## Desvios conscientes do diagrama

- **`app_user.password_hash`** — o diagrama pressupõe Supabase Auth, que o projeto não usa. A autenticação própria (JWT + PBKDF2) continua até a migração para Supabase Auth.
- **`app_user.name NOT NULL`** — o produto exige o nome no cadastro.
- **`app_user.fav_song_*` anuláveis** — o usuário é criado no cadastro, antes do onboarding. `onboarding_completed` não é coluna: é derivado de `fav_song_deezer_track_id IS NOT NULL`.
- **`genre.deezer_genre_id` e `genre.picture_url`** — o onboarding continua listando os gêneros do Deezer, com foto. O backend casa cada gênero com uma linha de `genre`, primeiro pelo id do Deezer e depois pelo nome. Se não encontrar, cria a linha. Os 18 gêneros do diagrama são semeados com UUIDs determinísticos (`uuid5`).
- **`recorda.song_cover_url` e `app_user.fav_song_cover_url`** aceitam `''`, porque uma faixa do Deezer pode não ter capa.
- **Tabela `media`** — fica fora do diagrama. É o armazenamento local que faz o papel do Supabase Storage.

## Consequências

- UUIDs são gerados na aplicação (`default=uuid.uuid4`). O `DEFAULT gen_random_uuid()` só existe na migration, porque não compila no SQLite.
- Os índices GIN `pg_trgm` só existem na migration e são ignorados pelo `--autogenerate`.
- Soft delete: repositórios filtram `deleted_at IS NULL`. As buscas usadas para checar se `username` e `email` já existem incluem os usuários excluídos, porque o índice UNIQUE continua ocupado por eles. As tabelas de favoritos não têm `deleted_at` e continuam com `DELETE` físico.
- `account_type` ('common'/'admin') virou `role` ('USER'/'ADMIN'). O `sub` do JWT agora é UUID, então todo token emitido antes desta mudança deixou de valer.
- `PUT` e `DELETE /recordas/{id}` passaram a exigir que o usuário seja o autor (403 caso contrário). `PUT` só altera `description`.
