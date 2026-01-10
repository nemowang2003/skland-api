from rich.text import Text

from skland_api.modules.sanity import SanityStatus
from skland_api.modules.sanity import main as module_entry

from . import render, render_capacity, render_timestamp


@render.register
def render_sanity_status(sanity_status: SanityStatus) -> Text:
    text = Text()

    text.append("预计当前理智", style="yellow bold")
    text.append(": ")
    text.append_text(render_capacity(sanity_status.sanity))
    text.append(" (")
    text.append_text(render_timestamp(sanity_status.full_at))
    text.append("回满)")

    return text


__all__ = ["module_entry"]
