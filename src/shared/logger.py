import json
import logging
import uuid
from contextvars import ContextVar
from typing import Any

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

logging.basicConfig(level=logging.INFO)


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def _emit(self, level: str, message: str, **kwargs: Any) -> None:
        entry = {
            "level": level,
            "message": message,
            "correlation_id": _correlation_id.get(),
            **kwargs,
        }
        getattr(self._logger, level.lower())(json.dumps(entry))

    def info(self, message: str, **kwargs: Any) -> None:
        self._emit("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._emit("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._emit("ERROR", message, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


def set_correlation_id(cid: str | None = None) -> str:
    cid = cid or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    return _correlation_id.get()
