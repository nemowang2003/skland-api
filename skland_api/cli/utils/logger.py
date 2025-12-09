import logging

import click


class LogFormatter(logging.Formatter):
    INDENT = 40

    def __init__(self, color: bool):
        self.color = color
        super().__init__(
            fmt="[{asctime}][{name}]{levelname}:{spaces}{message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )

    def format(self, record: logging.LogRecord) -> str:
        if self.color:
            _ = record.levelname, record.name
            color = {
                logging.CRITICAL: "bright_red",
                logging.ERROR: "red",
                logging.WARNING: "yellow",
                logging.INFO: "green",
                logging.DEBUG: "cyan",
            }
            record.levelname = click.style(
                record.levelname.lower(),
                fg=color[record.levelno],
                bold=True,
            )
            record.name = click.style(f"{record.name}", bold=True)
        used = len(record.levelname + record.name) + 20
        record.spaces = " " * max(0, self.INDENT - used)
        msg = super().format(record)
        if self.color:
            record.levelname, record.name = _
        return msg
