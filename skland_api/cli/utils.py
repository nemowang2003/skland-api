import sys
import time


def display_time(timestamp: int) -> str:
    """Display timestamp with a better format."""
    duration: int = timestamp - int(time.time())
    msg = ""

    if duration < 0:
        duration = abs(duration)
        suffix = "前"
    else:
        suffix = "后"

    days = duration // (24 * 60 * 60)
    hours = duration // (60 * 60) % 24
    minutes = duration // 60 % 60
    seconds = duration % 60
    """
    # implementation 1
    if days:
        msg += f"{days}天"

    if hours:
        msg += f"{hours}小时"
    elif msg:  # implies hours is 0
        msg += "0小时"

    if minutes:
        msg += f"{minutes}分钟"
    elif msg:  # implies minutes is 0
        msg += "0分钟"

    msg += f"{seconds}秒"
    """

    # implementation 2
    if days:
        msg += f"{days}d "
    msg += f"{hours:02}:{minutes:02}:{seconds:02}"

    return msg + suffix


def red_bold(msg: str) -> str:
    if not sys.stdout.isatty():
        return msg
    return f"\033[1;31m{msg}\033[m"


def green_bold(msg: str) -> str:
    if not sys.stdout.isatty():
        return msg
    return f"\033[1;32m{msg}\033[m"


def yellow_bold(msg: str) -> str:
    if not sys.stdout.isatty():
        return msg
    return f"\033[1;33m{msg}\033[m"
