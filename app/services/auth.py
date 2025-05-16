import os
from functools import wraps

from flask import request
from flask_smorest import abort
from loguru import logger

header = {
    "X-API-Key": {
        "description": "Chave de autenticação de autenticação da API",
        "type": "string",
    }
}


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("API_KEY")

        if not expected_key:
            logger.error("Chave de API não configurada no servidor")
            abort(500, message="Servidor não configurado corretamente")

        if not api_key:
            logger.error("Requisição sem chave de API")
            abort(401, message="Chave de API ausente")

        if api_key != expected_key:
            logger.error("Chave de API inválida")
            abort(401, message="Chave de API inválida")

        return f(*args, **kwargs)

    return decorated
