import os


class Config:
    # SQLAlchemy Config
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 30,
        "pool_recycle": 3600,
    }
    # Apscheduler Config
    SCHEDULER_API_ENABLED = True
    APSCHEDULER_JOB_DEFAULTS = {"coalesce": True, "max_instances": 1}
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
