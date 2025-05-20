import pytest
from flask import Flask
from app import create_app


@pytest.fixture
def app() -> Flask:
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    return app


@pytest.fixture
def client(app: Flask):  # noqa: ANN201
    return app.test_client()
