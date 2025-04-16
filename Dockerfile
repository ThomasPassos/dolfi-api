FROM python:3.12-slim as builder

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

# 1. Instalar Poetry e dependências de compilação
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev \
    && pip install --no-cache-dir poetry

# 2. Copiar e instalar dependências
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi --no-root

# 3. Instalar Gunicorn explicitamente
RUN pip install --no-cache-dir gunicorn==23.0.0

# 4. Copiar aplicação
COPY . .

# ----------------------------
# Estágio de produção final
# ----------------------------
FROM python:3.12-slim
WORKDIR /app

# 5. Copiar dependências e Gunicorn
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=builder /app /app

# 6. Garantir permissões e PATH
ENV PATH="/usr/local/bin:${PATH}" \
    PYTHONPATH=/app

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]