import sys
import json
from datetime import datetime
from loguru import logger
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO", format: str = "json") -> None:
    """Configure structured logging for the application."""

    # Remove default handler
    logger.remove()

    if format == "json":
        # JSON logging for production
        log_format = "%(time)s %(level)s %(name)s %(message)s"

        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)
                log_record["timestamp"] = datetime.utcnow().isoformat()
                log_record["level"] = record.levelname
                log_record["logger"] = record.name

        handler = sys.stdout
        formatter = CustomJsonFormatter(log_format)
        handler = jsonlogger.JsonFormatterAwareHandler(
            formatter=formatter, stream=handler
        )

        logger.add(
            handler,
            format=log_format,
            level=log_level,
            serialize=True,
        )
    else:
        # Human-readable logging for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True,
        )


def get_logger(name: str = None):
    """Get a configured logger instance."""
    if name:
        return logger.bind(logger=name)
    return logger
