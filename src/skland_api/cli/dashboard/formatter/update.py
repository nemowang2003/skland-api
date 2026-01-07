from rich.text import Text

from skland_api.modules.update import UpdateStatus
from skland_api.modules.update import main as module_entry

from . import render, render_timestamp


@render.register
def render_update_status(update_status: UpdateStatus) -> Text:
    text = Text()

    text.append("上次在线时间", style="yellow bold")
    text.append(": ")
    text.append_text(render_timestamp(update_status.last_update_at))
    text.append("\n")

    return text


__all__ = ["module_entry"]
