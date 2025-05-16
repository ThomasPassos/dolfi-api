import os


class Config:
    # OpenAPI Config
    API_TITLE = "Dolfi API"
    API_VERSION = "0.0.1"
    OPENAPI_VERSION = "3.0.2"
    # SQLAlchemy Config
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 30,
        "pool_recycle": 3600,
    }
    # Cache Config
    CACHE_TYPE = "RedisCache"
    CACHE_DEFAULT_TIMEOUT = 600
    CACHE_REDIS_URL = os.getenv("REDIS_URL")
    # ... outras configurações
    CELERY = {
        "broker_url": os.getenv("REDIS_URL"),
        "result_backend": os.getenv("REDIS_URL"),
        "TIMEZONE": "America/Sao_Paulo",
    }
