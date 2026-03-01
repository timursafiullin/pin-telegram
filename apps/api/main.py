import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from apps.api.routers import bot, users, events
from apps.config import settings


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"
        return super().format(record)


class RequestPrefixFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "log_prefix"):
            record.log_prefix = "[APP]"
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    request_filter = RequestPrefixFilter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(root.level)
    console_handler.addFilter(request_filter)
    console_handler.setFormatter(
        ColorFormatter("%(asctime)s | %(levelname)s | %(log_prefix)s %(name)s | %(message)s")
    )

    log_path = Path(settings.LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setLevel(root.level)
    file_handler.addFilter(request_filter)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(log_prefix)s %(name)s | %(message)s")
    )

    root.addHandler(console_handler)
    root.addHandler(file_handler)


configure_logging()


def create_app() -> FastAPI:
    app = FastAPI(title="Personal Intelligence Node API")
    app.include_router(bot.router, prefix="/bot")
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(events.router, prefix="/events", tags=["events"])
    return app


app = create_app()
