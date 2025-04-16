# Dockerfile final otimizado
FROM python:3.12-slim as builder

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# 1. Instalar Poetry
RUN pip install --no-cache-dir poetry

# 2. Copiar apenas dependências
COPY pyproject.toml poetry.lock ./

# 3. Instalar dependências no Python global
RUN poetry install --only main --no-ansi --no-root

# 4. Copiar o restante do código
COPY . .

# 5. Configuração final de produção
FROM python:3.12-slim as runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]