from contextlib import contextmanager

import click
import time


def display_remain_seconds(duration: int, with_suffix: bool = True) -> str:
    if duration < 0:
        duration = abs(duration)
        suffix = "前"
    else:
        suffix = "后"
    days = duration // (24 * 60 * 60)
    hours = duration // (60 * 60) % 24
    minutes = duration // 60 % 60
    seconds = duration % 60

    msg = ""
    if days:
        msg += f"{days}d "
    msg += f"{hours:02}:{minutes:02}:{seconds:02}"

    return msg + suffix if with_suffix else ""


def display_timestamp(timestamp: int) -> str:
    """Display timestamp with a better format."""
    duration: int = timestamp - int(time.time())

    return display_remain_seconds(duration)


def display_capacity_or_progress(
    current: int,
    total: int,
    capacity: bool = False,
    progress: bool = False,
) -> str:
    if not capacity ^ progress:
        raise ValueError("'capacity' and 'progress' should be mutual exclusive")

    if current < total and progress or current == total and capacity:
        fg = "red"
    else:
        fg = "green"
    return click.style(f"{current}/{total}", fg=fg, bold=True)


class Formatter:
    def __init__(self) -> None:
        self.indent_width: int = 0
        self.buffer: list[str] = []
        self.ready_depth: int = 0
        self.at_line_start: bool = True

    def write(self, *msgs: str) -> None:
        for msg in msgs:
            if self.at_line_start:
                msg = " " * self.indent_width + msg
            if self.ready_depth:
                self.buffer.append(msg)
            else:
                click.echo(msg, nl=False)
            self.at_line_start = msg.endswith("\n")

    def writeline(self, msg: str) -> None:
        if self.at_line_start:
            msg = " " * self.indent_width + msg
        if self.ready_depth:
            if not msg.endswith("\n"):
                msg += "\n"
            self.buffer.append(msg)
        else:
            click.echo(msg)
        self.at_line_start = True

    def flush(self):
        click.echo("".join(self.buffer), nl=False)
        self.buffer.clear()

    @contextmanager
    def ready(self):
        self.ready_depth += 1
        try:
            yield
        finally:
            self.ready_depth -= 1
            if self.ready_depth == 0:
                self.flush()

    @contextmanager
    def indent(self, n: int = 2):
        if not self.at_line_start:
            self.write("\n")
        self.indent_width += n
        try:
            yield
        finally:
            self.indent_width -= n
            if not self.at_line_start:
                self.write("\n")

    def write_style(
        self,
        msg: str,
        prefix: str = "",
        suffix: str = "",
        **kwargs,
    ) -> None:
        self.write(prefix, click.style(msg, **kwargs), suffix)

    def write_green_bold(self, msg: str, prefix: str = "", suffix: str = "") -> None:
        self.write_style(
            msg,
            prefix,
            suffix,
            fg="green",
            bold=True,
        )

    def write_yellow_bold(self, msg: str, prefix: str = "", suffix: str = "") -> None:
        self.write_style(
            msg,
            prefix,
            suffix,
            fg="yellow",
            bold=True,
        )

    def write_red_bold(self, msg: str, prefix: str = "", suffix: str = "") -> None:
        self.write_style(
            msg,
            prefix,
            suffix,
            fg="red",
            bold=True,
        )
