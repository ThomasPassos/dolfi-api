import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):  # noqa: PLR6301
        try:
            level = logger.level(record.levelname).name
        except KeyError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
