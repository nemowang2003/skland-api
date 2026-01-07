from rich.text import Text

from skland_api.modules.routine import RoutineStatus
from skland_api.modules.routine import main as module_entry

from . import render, render_progress, render_timestamp


@render.register
def render_routine_status(routine_status: RoutineStatus) -> Text:
    text = Text()

    text.append("剿灭作战进度", style="yellow bold")
    text.append(": ")
    text.append_text(render_progress(routine_status.annihilation))
    text.append(" (预计")
    text.append_text(render_timestamp(routine_status.annihilation_reset_at))
    text.append("周期结束)\n")

    text.append("保全派驻进度", style="yellow bold")
    text.append(": ")
    text.append_text(render_progress(routine_status.sss_instrument))
    text.append(", ")
    text.append_text(render_progress(routine_status.sss_component))
    text.append(" (预计")
    text.append_text(render_timestamp(routine_status.sss_reset_at))
    text.append("周期结束)\n")

    return text


__all__ = ["module_entry"]
