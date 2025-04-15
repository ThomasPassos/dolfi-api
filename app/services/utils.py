import logging
import os
from functools import wraps

from flask import jsonify, request

logger = logging.getLogger(__name__)


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("API_KEY")
        if not api_key:
            logger.warning("Requisição sem chave de API")
            return jsonify({"error": "Chave de API ausente"}), 401
        if api_key != expected_key:
            logger.warning("Chave de API inválida")
            return jsonify({"error": "Chave de API inválida"}), 401
        return f(*args, **kwargs)

    return decorated
