class Config:
    # SQLAlchemy Config
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:pYOeKwirVaEVfzCbTcJAgCWCASJxAhXF@centerbeam.proxy.rlwy.net:22522/railway"
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
    CACHE_REDIS_URL = "redis://default:YQByOHmGyTRwOWqGknFnwDkXgwiuNOtS@shuttle.proxy.rlwy.net:44861"
    # ... outras configurações
    CELERY = {
        "broker_url": "redis://default:YQByOHmGyTRwOWqGknFnwDkXgwiuNOtS@shuttle.proxy.rlwy.net:44861",
        "result_backend": "redis://default:YQByOHmGyTRwOWqGknFnwDkXgwiuNOtS@shuttle.proxy.rlwy.net:44861",
        "TIMEZONE": "America/Sao_Paulo",
    }
