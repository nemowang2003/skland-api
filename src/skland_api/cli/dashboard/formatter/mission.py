from rich.text import Text

from skland_api.modules.mission import MissionStatus
from skland_api.modules.mission import main as module_entry

from . import render, render_progress


@render.register
def render_mission_status(mission_status: MissionStatus) -> Text:
    text = Text()

    text.append("日常任务", style="yellow bold")
    text.append(": ")
    text.append_text(render_progress(mission_status.daily))
    text.append("\n")

    text.append("周常任务", style="yellow bold")
    text.append(": ")
    text.append_text(render_progress(mission_status.weekly))
    text.append("\n")

    return text


__all__ = ["module_entry"]
