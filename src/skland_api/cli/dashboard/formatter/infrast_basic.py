from rich.panel import Panel
from rich.text import Text

from skland_api.modules.infrast_basic import InfrastOverview
from skland_api.modules.infrast_basic import main as module_entry

from . import render, render_capacity, render_duration


@render.register
def render_infrast_overview(infrast_overview: InfrastOverview) -> Panel:
    text = Text()

    if infrast_overview.exhausted_operators:
        text.append("疲劳干员", style="yellow bold")
        text.append(":")
        for operator_name in infrast_overview.exhausted_operators:
            text.append(" ")
            text.append(operator_name, style="red bold")
        text.append("\n")

    text.append("预计无人机数量", style="yellow bold")
    text.append(": ")
    text.append_text(render_capacity(infrast_overview.drones))
    text.append(" (预计")
    text.append_text(render_duration(infrast_overview.drones_full_in))
    text.append("补满)\n")

    if infrast_overview.mastery is not None:
        mastery = infrast_overview.mastery

        text.append("专精干员", style="yellow bold")
        text.append(": ")
        text.append(mastery.trainee_name, style="green bold")
        skill_id = mastery.skill_id + 1
        level = mastery.skill_mastery_level + 1
        text.append(f"({skill_id}技能, 专精等级{level}->{level + 1})\n")

        if mastery.trainer_name is not None:
            text.append("协助干员", style="yellow bold")
            text.append(": ")
            text.append(mastery.trainer_name, style="green bold")
            text.append("\n")

        text.append("专精进度", style="yellow bold")
        text.append(": ")
        current = mastery.progress.current
        total = mastery.progress.total
        text.append(f"{current / total * 100:.2f}%")
        text.append(" (预计")
        text.append_text(render_duration(mastery.remain_seconds))
        text.append("完成)\n")

    return Panel(text, title="基建概览")


__all__ = ["module_entry"]
