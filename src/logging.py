import logging
import sys
from typing import Literal


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    json_format: bool = False,
) -> logging.Logger:
    if json_format:
        log_format = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        log_format = "%(asctime)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    return logging.getLogger("ygo_pipelines")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"ygo_pipelines.{name}")
