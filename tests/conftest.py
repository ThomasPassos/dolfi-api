import pytest
from flask import Flask, Response
from flask.testing import FlaskClient

from app import create_app


@pytest.fixture
def app() -> Flask:
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient[Response]:
    return app.test_client()
