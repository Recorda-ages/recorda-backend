"""Global exception handlers that standardize every error response to:

{
    "error": {
        "code": "ERROR_CODE",
        "message": "Mensagem do erro",
        "details": {}
    }
}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}

STATUS_MESSAGES: dict[int, str] = {
    400: "Requisição inválida",
    401: "Não autorizado",
    403: "Acesso negado",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    409: "Conflito",
    422: "Dados inválidos",
    429: "Muitas requisições",
    500: "Erro interno do servidor",
    502: "Gateway inválido",
    503: "Serviço indisponível",
    504: "Tempo limite do gateway",
}


def get_error_code(status_code: int) -> str:
    return STATUS_CODES.get(status_code, f"HTTP_{status_code}")


def get_error_message(status_code: int) -> str:
    return STATUS_MESSAGES.get(status_code, "Erro inesperado")


def _error_body(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields = []
    for err in exc.errors():
        loc = err.get("loc", [])
        fields.append(
            {
                "field": loc[-1] if loc else None,
                "message": _TRANSLATED_MSG.get(err.get("msg"), err.get("msg")),
            }
        )
    details = {"fields": fields} if fields else {}
    return JSONResponse(
        status_code=422,
        content=_error_body("VALIDATION_ERROR", get_error_message(422), details),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
    else:
        message = get_error_message(exc.status_code)
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(get_error_code(exc.status_code), message),
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body(get_error_code(500), get_error_message(500)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


_TRANSLATED_MSG = {
    "Field required": "Campo obrigatório não informado",
    "field required": "Campo obrigatório não informado",
}
