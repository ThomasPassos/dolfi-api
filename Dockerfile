# Dockerfile
FROM python:3.12-alpine
WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "16", "app:create_app()"]