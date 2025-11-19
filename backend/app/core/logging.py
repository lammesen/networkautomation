from __future__ import annotations

import logging
from logging.config import dictConfig

from .config import settings


def setup_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": settings.log_level,
            },
        }
    )


setup_logging()
