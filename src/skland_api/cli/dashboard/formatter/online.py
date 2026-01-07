from rich.text import Text

from skland_api.modules.online import OnlineStatus
from skland_api.modules.online import main as module_entry

from . import render, render_timestamp


@render.register
def render_online_status(online_status: OnlineStatus) -> Text:
    text = Text()

    text.append("上次在线时间", style="yellow bold")
    text.append(": ")
    text.append_text(render_timestamp(online_status.last_online_at))

    return text.append("\n")


__all__ = ["module_entry"]
