# recorda-backend

Repositório para o backend do projeto Recorda.

Backend em **Python + FastAPI**, com **SQLAlchemy** como ORM e **PostgreSQL** como banco de dados.

## Requisitos

Para o ambiente recomendado, é necessário apenas:

- [Docker](https://www.docker.com/)
- Docker Compose (incluído nas versões atuais do Docker Desktop)

O projeto utiliza **Python 3.13** dentro do container, portanto não é necessário instalar Python ou PostgreSQL localmente para executar o backend com Docker.

## Como rodar o projeto com Docker

O ambiente Docker é a forma recomendada de executar o projeto, pois padroniza a configuração do backend e do PostgreSQL para todos os desenvolvedores.

A arquitetura local é:

```text
Frontend
   |
   | HTTP
   v
Backend (FastAPI)
localhost:8000
   |
   | PostgreSQL
   v
PostgreSQL
container "db"
```

### 1. Clone o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd recorda-backend
```

### 2. Configure o arquivo `.env`

Copie o arquivo de exemplo:

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

**Windows (CMD):**

```cmd
copy .env.example .env
```

**Linux/macOS:**

```bash
cp .env.example .env
```

Para o ambiente Docker, a configuração do banco utilizada pelo backend deve apontar para o serviço `db`, e não para `localhost`.

Exemplo:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=recorda

APP_NAME=Recorda API
ENVIRONMENT=development
DEBUG=true
VERSION=0.1.0

CORS_ORIGINS=http://localhost:8081,http://127.0.0.1:8081
```

> **Importante:** não configure `DATABASE_URL` no `.env` apontando para `localhost` quando estiver utilizando o Docker Compose. Dentro do container da API, `localhost` representa o próprio container. O PostgreSQL é acessado pelo nome do serviço `db`.

A conexão utilizada pelo Compose segue o formato:

```text
postgresql+psycopg://USUARIO:SENHA@db:5432/BANCO
```

O arquivo `.env` contém configurações locais e credenciais e não deve ser versionado.

> **Sessões:** defina `ACCESS_TOKEN_SECRET_KEY` com um valor fixo. Sem ele, a API gera um segredo aleatório a cada inicialização e todos os tokens emitidos antes deixam de ser válidos (o app volta para o Login a cada restart). Em produção a variável é obrigatória.

### 3. Construa e inicie os containers

Na raiz do projeto, execute:

```bash
docker compose up --build
```

O Docker Compose irá:

1. Construir a imagem do backend a partir do `Dockerfile`;
2. Criar o container da API;
3. Criar o container do PostgreSQL;
4. Criar o volume persistente do PostgreSQL;
5. Aguardar o PostgreSQL ficar saudável;
6. Iniciar a API.

A API ficará disponível em:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/api/v1/health
```

### 4. Verifique o estado dos containers

Em outro terminal:

```bash
docker compose ps
```

O serviço `db` deve estar saudável antes que a API seja considerada pronta.

Para acompanhar os logs:

```bash
docker compose logs -f
```

Somente da API:

```bash
docker compose logs -f api
```

Somente do PostgreSQL:

```bash
docker compose logs -f db
```

## Parar e reiniciar o ambiente

Para parar os containers:

```bash
docker compose down
```

Para iniciar novamente sem reconstruir as imagens:

```bash
docker compose up
```

Se alguma dependência ou configuração do Dockerfile tiver sido alterada, reconstrua a imagem:

```bash
docker compose up --build
```

### Persistência do banco

O PostgreSQL utiliza um volume Docker chamado `pgdata`.

Portanto:

```bash
docker compose down
```

não apaga os dados do banco.

**Atenção:** o comando abaixo remove também os volumes e, consequentemente, os dados locais do PostgreSQL:

```bash
docker compose down -v
```

Use `down -v` somente quando realmente quiser recriar o banco do zero.

## Desenvolvimento sem Docker

O ambiente Docker é o procedimento recomendado para o projeto. Ainda assim, o backend pode ser executado diretamente com Python caso seja necessário.

### 1. Crie e ative o ambiente virtual

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Instale as dependências

```bash
pip install -e .
```

Isso instala as dependências declaradas no `pyproject.toml`, entre outras as bibliotecas `fastapi`, `uvicorn`, `sqlalchemy` e `psycopg`.

### 3. Configure o PostgreSQL local

Ao executar o backend fora do Docker, o PostgreSQL precisa estar instalado e em execução na máquina.

Nesse cenário, a `DATABASE_URL` deve apontar para `localhost`, por exemplo:

```ini
DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@localhost:5432/recorda
```

Crie o banco de dados, caso ainda não exista:

```bash
psql -U postgres -c "CREATE DATABASE recorda;"
```

### 4. Inicie o servidor

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em:

```text
http://localhost:8000
```

> **Importante:** não misture as configurações de banco dos dois ambientes. Com Docker, o host do PostgreSQL é `db`. Sem Docker, o host normalmente é `localhost`.

## Banco de dados

O backend utiliza:

- PostgreSQL 16 no ambiente Docker;
- SQLAlchemy como ORM;
- `psycopg` como driver PostgreSQL.

O schema segue o diagrama oficial do banco (wiki AGES → *Banco de Dados*) e é versionado com **Alembic** (`alembic/versions/`). A aplicação não cria tabelas ao iniciar: no Docker, o `docker-entrypoint.sh` roda `alembic upgrade head` antes de subir o uvicorn.

Sem Docker, aplique as migrations manualmente:

```bash
alembic upgrade head
```

Para alterar o schema, edite os models em `app/models/` e gere uma nova migration:

```bash
alembic revision --autogenerate -m "descricao da mudanca"
# revise o arquivo gerado em alembic/versions/ antes de commitar
alembic upgrade head
alembic check   # deve responder "No new upgrade operations detected."
```

Nunca edite uma migration que já foi mergeada na `dev` — crie outra.

Os índices GIN `pg_trgm` só existem nas migrations (não são portáveis para o SQLite dos testes) e são ignorados pelo `--autogenerate`.

### Banco criado antes do Alembic

Se o seu volume `pgdata` foi criado pela versão antiga (que usava `create_all`), marque-o como estando no baseline antes do primeiro upgrade:

```bash
docker compose up -d db
docker compose run --rm api alembic stamp 0001_baseline
docker compose run --rm api alembic upgrade head
```

A migration `0002_diagram_schema` **recria** `users`, `recordas` e `music_preferences` como `app_user`, `recorda`, `genre`, `user_favorite_genre` e `user_favorite_artist`: os dados dessas tabelas não são preservados. Todos os tokens emitidos antes dela deixam de valer, então é preciso cadastrar a conta de novo. Se preferir, `docker compose down -v` recria o banco do zero.

## CORS

O backend utiliza a variável de ambiente `CORS_ORIGINS` para definir quais origens podem realizar requisições à API.

Exemplo:

```ini
CORS_ORIGINS=http://localhost:8081,http://127.0.0.1:8081
```

A porta deve corresponder à porta em que o frontend está sendo executado.

Não utilize `*` para liberar todas as origens.

Se a porta do frontend mudar, atualize `CORS_ORIGINS` no `.env` antes de iniciar os containers.

## Endpoints

### Saúde

| Método | Caminho | Descrição |
| ------ | ------- | --------- |
| GET | `/` | Health check básico `{"status":"ok"}` |
| GET | `/api/v1/health` | Status da aplicação (nome + versão) |

### Usuários

| Método | Caminho | Descrição |
| ------ | ------- | --------- |
| GET | `/api/v1/users` | Lista os usuários ativos (admin) |
| POST | `/api/v1/users` | Cria um usuário (`name`, `email`, `username`, `password`) |
| GET | `/api/v1/users/{user_id}` | Retorna um usuário (UUID; 404 se não existir) |
| PUT | `/api/v1/users/{user_id}` | Atualiza um usuário (admin) |
| DELETE | `/api/v1/users/{user_id}` | Soft delete: preenche `deleted_at` (admin) |
| PATCH | `/api/v1/users/{user_id}/role` | Altera o papel (`USER` / `ADMIN`) (admin) |
| POST | `/api/v1/users/me/music-preferences` | Salva gêneros, artistas e música favorita do onboarding |

Os identificadores são UUID (`user_id`, `recorda_id`). Nenhuma rota apaga linhas fisicamente: exclusões preenchem `deleted_at`, e as consultas ignoram registros excluídos.

## Testes

O projeto utiliza **pytest** com cobertura mínima de 80% configurada no `pyproject.toml`.

### Instalação das dependências de teste

Ative o ambiente virtual e instale o grupo `test`:

```bash
pip install -e ".[test]"
```

### Executar todos os testes

```bash
pytest
```

Esse comando já inclui o relatório de cobertura no terminal e gera o arquivo `coverage-unit.xml`, conforme configurado em `pyproject.toml`.

### Executar com relatório de cobertura detalhado

```bash
pytest --cov=app --cov-report=term-missing
```

Exibe quais linhas de cada módulo não foram cobertas pelos testes.


## Estrutura do projeto

```text
recorda-backend/
├── app/
│   ├── main.py              # Entrypoint do FastAPI (registra roteadores + lifespan)
│   ├── core/
│   │   └── config.py        # Configurações via pydantic-settings (.env)
│   ├── db/
│   │   ├── session.py       # Engine, sessão e Base do SQLAlchemy
│   │   └── __init__.py      # Reexporta helpers do banco
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # Modelo ORM User
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Modelos Pydantic de request/response
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── user_repository.py  # Acesso/persistência no banco
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py     # Regras de negócio e orquestração
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           ├── health.py    # Router de saúde
│           └── user.py      # Router HTTP (chama o service)
├── Dockerfile               # Imagem do backend
├── docker-compose.yml       # Backend + PostgreSQL
├── .dockerignore            # Arquivos excluídos da imagem
├── .env.example             # Exemplo de variáveis de ambiente
├── pyproject.toml           # Dependências e metadados do projeto
└── README.md
```

## Resumo da arquitetura

- **`core/`** — configuração e itens independentes de framework.
- **`db/`** — engine, sessão e Base do SQLAlchemy.
- **`models/`** — classes ORM que mapeiam as tabelas do banco.
- **`schemas/`** — modelos Pydantic de entrada/saída da API.
- **`repositories/`** — acesso e persistência no banco (queries).
- **`services/`** — regras de negócio e orquestração dos fluxos.
- **`api/routes/`** — roteadores FastAPI (camada HTTP).
- **`Dockerfile`** — define a imagem utilizada pela API.
- **`docker-compose.yml`** — orquestra a API e o PostgreSQL.
- **`pgdata`** — volume persistente utilizado pelo PostgreSQL.

## Comandos Docker úteis

| Comando | Função |
| ------- | ------ |
| `docker compose up --build` | Constrói as imagens e inicia o ambiente |
| `docker compose up` | Inicia o ambiente existente |
| `docker compose down` | Para e remove os containers, preservando o banco |
| `docker compose down -v` | Remove containers e volumes, apagando os dados locais |
| `docker compose ps` | Mostra o estado dos serviços |
| `docker compose logs -f` | Acompanha os logs |
| `docker compose logs -f api` | Acompanha somente os logs da API |
| `docker compose build --no-cache` | Reconstrói as imagens sem utilizar cache |
