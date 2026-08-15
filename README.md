# recorda-backend
Repositório para o backend do projeto Recorda.

Backend em **Python + FastAPI**.

## Requisitos

- Python 3.10+
- venv (opcional, recomendado)

## Configuração

1. Crie e ative o ambiente virtual:

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure as variáveis de ambiente:

   ```bash
   cp .env.example .env
   ```

4. Inicie o servidor de desenvolvimento:

   ```bash
   uvicorn app.main:app --reload
   ```

## Endpoints

| Método | Caminho    | Descrição                          |
| ------ | ---------- | ---------------------------------- |
| GET    | `/`        | Health check básico `{"status":"ok"}`
| GET    | `/health`  | Status da aplicação (nome + versão)|
| GET    | `/docs`    | Documentação interativa (Swagger)  |

## Estrutura do projeto

```
.
├── app/
│   ├── main.py          # Entrypoint do FastAPI
│   ├── config.py        # Configurações via pydantic-settings (.env)
│   ├── schemas.py       # Modelos Pydantic de request/response
│   └── routers/
│       ├── __init__.py
│       └── health.py    # Exemplo de router
├── .env.example         # Exemplo de variáveis de ambiente
├── requirements.txt
└── README.md
```
