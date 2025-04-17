# Dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi
COPY . .
RUN lsof -i :8080
CMD ["gunicorn", "-c", "gunicorn.conf.py","app:create_app()"]