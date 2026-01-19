from functools import singledispatch

from rich.console import RenderableType
from rich.text import Text

from skland_api.models import Capacity, Duration, Progress, TimeStamp


@singledispatch
def render(data) -> RenderableType:
    return str(data)


def render_capacity(capacity: Capacity) -> Text:
    if capacity.current >= capacity.total:
        color = "red"
    else:
        color = "green"
    return Text(f"{capacity.current}/{capacity.total}", style=f"bold {color}")


def render_progress(progress: Progress) -> Text:
    if progress.current < progress.total:
        color = "red"
    else:
        color = "green"
    return Text(f"{progress.current}/{progress.total}", style=f"bold {color}")


def render_duration(duration: Duration) -> Text:
    if duration < 0:
        duration = abs(duration)
        suffix = "前"
    else:
        suffix = "后"
    days = duration // (24 * 60 * 60)
    hours = duration // (60 * 60) % 24
    minutes = duration // 60 % 60
    seconds = duration % 60

    if days:
        msg = f"{days}d {hours:02}:{minutes:02}:{seconds:02}{suffix}"
    else:
        msg = f"{hours:02}:{minutes:02}:{seconds:02}{suffix}"

    return Text(msg)


def render_timestamp(timestamp: TimeStamp) -> Text:
    return render_duration(Duration.from_now(timestamp))
