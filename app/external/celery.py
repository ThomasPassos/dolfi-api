from celery import Celery
from flask import Flask

celery = Celery(__name__)


def init_celery(app: Flask):
    celery.conf.update(app.config)
    celery.conf.update(
        task_serializer='pickle',
        result_serializer='pickle',
        accept_content=['pickle', 'json']
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
