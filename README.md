# recorda-backend

Repositório para o backend do projeto Recorda.

Backend em **Python + FastAPI**, com **SQLAlchemy** como ORM e **PostgreSQL** como banco de dados.

## Requisitos

- Python 3.10+ (projeto desenvolvido com Python 3.13)
- PostgreSQL (instalado e rodando)

## Como rodar o projeto

### 1. Crie e ative o ambiente virtual

```bash
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux/macOS:
python3 -m venv venv && source venv/bin/activate
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

Isso instala, entre outras, as bibliotecas `fastapi` (API), `uvicorn` (servidor), `sqlalchemy` (ORM) e `psycopg` (driver do PostgreSQL).

### 3. Instale e configure o PostgreSQL

Se ainda não tiver o PostgreSQL instalado, baixe-o em [postgresql.org](https://www.postgresql.org/download/). No Windows, durante a instalação, lembre-se de marcar a opção de adicionar `psql` ao PATH.

Crie o banco de dados que a aplicação usará:

```bash
psql -U postgres -c "CREATE DATABASE recorda;"
```

A tabela `users` é criada automaticamente pela aplicação ao iniciar — não é necessário rodar migrações.

### 4. Configure o arquivo `.env`

Copie o exemplo e ajuste os valores:

```bash
# Windows:
copy .env.example .env
# Linux/macOS:
cp .env.example .env
```

Edite o `.env` e preencha a `DATABASE_URL` com as credenciais do seu PostgreSQL:

```ini
APP_NAME=Recorda API
ENVIRONMENT=development
DEBUG=true
VERSION=0.1.0
DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@localhost:5432/recorda
```

Substitua `USUARIO` e `SENHA` pelo usuário e senha do seu PostgreSQL (o padrão costuma ser `postgres`/`postgres`), e `recorda` pelo nome do banco que você criou.

> **Nota:** o `.env` contém credenciais e não deve ser versionado — ele já está no `.gitignore`.

### 5. Inicie o servidor de desenvolvimento

```bash
uvicorn app.main:app --reload
```

O servidor inicia em `http://localhost:8000`. Ao subir, ele cria a tabela `users` automaticamente. Acesse `http://localhost:8000/docs` (Swagger) para testar os endpoints.

## Endpoints

### Saúde

| Método | Caminho   | Descrição                          |
| ------ | --------- | ---------------------------------- |
| GET    | `/`       | Health check básico `{"status":"ok"}` |
| GET    | `/health` | Status da aplicação (nome + versão) |

### Usuários (exemplo com o ORM)

| Método | Caminho        | Descrição                            |
| ------ | -------------- | ------------------------------------ |
| GET    | `/users`       | Lista todos os usuários              |
| POST   | `/users`       | Cria um usuário (`name`, `email`)    |
| GET    | `/users/{id}`  | Retorna um usuário (404 se não existir) |
| PUT    | `/users/{id}`  | Atualiza um usuário                  |
| DELETE | `/users/{id}`  | Remove um usuário                    |

Exemplo de criação de um usuário (`POST /users`):

```json
{
  "name": "Maria Silva",
  "email": "maria@example.com"
}
```

## Estrutura do projeto

```
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
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           ├── health.py    # Router de saúde
│           └── user.py      # CRUD de usuários (usa o ORM)
├── .env.example             # Exemplo de variáveis de ambiente
├── requirements.txt
└── README.md
```

## Resumo da arquitetura

- **`core/`** — configuração e itens independentes de framework.
- **`db/`** — engine, sessão e Base do SQLAlchemy (camada de acesso ao banco).
- **`models/`** — classes ORM que mapeiam as tabelas do banco.
- **`schemas/`** — modelos Pydantic de entrada/saída da API.
- **`api/routes/`** — roteadores FastAPI (camada HTTP).
