from rich.panel import Panel
from rich.text import Text

from skland_api.modules.recruit import RecruitOverview
from skland_api.modules.recruit import main as module_entry

from . import render, render_capacity, render_timestamp


@render.register
def render_recruit_overview(recruit_overview: RecruitOverview) -> Panel:
    text = Text()

    for index, recruit in enumerate(recruit_overview.recruits, start=1):
        text.append(f"栏位{index}", style="yellow bold")
        text.append(": ")
        if recruit.is_idle or recruit.finish_at is None:
            text.append("空闲", style="green bold")
        else:
            text.append_text(render_timestamp(recruit.finish_at))
            text.append("招募完毕")
        text.append("\n")

    text.append("刷新次数", style="yellow bold")
    text.append(": ")
    text.append_text(render_capacity(recruit_overview.refresh))
    if recruit_overview.refresh_at is not None:
        text.append(" (预计")
        text.append_text(render_timestamp(recruit_overview.refresh_at))
        text.append("刷新)")

    return Panel(text, title="公招概览")


__all__ = ["module_entry"]
