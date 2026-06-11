import os, sys, logging
from logging import LoggerAdapter, LogRecord
from logging.handlers import RotatingFileHandler


def setup_logging(use_console: bool = True) -> logging.Logger:

    def context_filter(record: LogRecord) -> bool:
        """로그 레코드 필드 보정 함수"""
        for key in ("operation_id", "user_id", "affiliation", "action"):
            if not hasattr(record, key):
                setattr(record, key, "-")
        return True

    def formatter():
        fmt = (
            "[%(asctime)s] [%(levelname)s] [%(name)s] "
            "[op=%(operation_id)s] [user=%(user_id)s] "
            "[aff=%(affiliation)s] [act=%(action)s] %(message)s"
        )
        return logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S")

    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("fastapi_server")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        return logger

    fmt = formatter()

    fh = RotatingFileHandler("logs/server.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if use_console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    logger.addFilter(context_filter)
    return logger


def get_request_logger(operation_id="-", user_id="-", affiliation="-", action="-") -> LoggerAdapter:
    base = logging.getLogger("fastapi_server")
    return LoggerAdapter(base, {
        "operation_id": operation_id,
        "user_id": user_id,
        "affiliation": affiliation,
        "action": action,
    })
