from rich.text import Text

from skland_api.modules.update import UpdateStatus
from skland_api.modules.update import main as module_entry

from . import render, render_timestamp


@render.register
def render_update_status(update_status: UpdateStatus) -> Text:
    text = Text()

    text.append("更新于")
    text.append_text(render_timestamp(update_status.last_update_at))

    return text


__all__ = ["module_entry"]
