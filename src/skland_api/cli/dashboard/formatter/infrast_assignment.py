from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from skland_api.modules.infrast_assignment import (
    FacilityAudit,
    InfrastAssignmentReport,
    StationedOperatorInfo,
)
from skland_api.modules.infrast_assignment import main as module_entry

from . import render, render_timestamp

MORALE_REDLINE = 8


def render_facility_audit(facility_audit: FacilityAudit) -> Text:
    text = Text()
    for operator_name in facility_audit.missing:
        text.append(" ")
        text.append(operator_name, style="s red bold")
    for operator in facility_audit.present:
        text.append(" ")
        text.append(operator.name, style="bold")
    for operator in facility_audit.unexpected:
        text.append(" ")
        text.append(operator.name, style="u green bold")
    return text.append("\n")


def render_stationed_operator(operator: StationedOperatorInfo) -> Text:
    text = Text()
    text.append(operator.name, style="bold")
    text.append(": ")
    morale_color = "green" if operator.morale > MORALE_REDLINE else "red"
    text.append(f"{operator.morale:.2f}", style=f"{morale_color} bold")
    return text


@render.register
def render_infrast_assignment(infrast_assignment: InfrastAssignmentReport) -> Group:
    group_elements = []

    audit = infrast_assignment.audit
    if audit is not None:
        text = Text()

        text.append("控制中枢", style="bold")
        text.append(":")
        text.append(render_facility_audit(audit.control))

        for facility in audit.powers:
            text.append("发电站", style="green bold")
            text.append(":")
            text.append(render_facility_audit(facility))

        for facility in audit.tradings:
            text.append("贸易站", style="blue bold")
            text.append(":")
            text.append(render_facility_audit(facility))

        for facility in audit.manufactures:
            text.append("制造站", style="yellow bold")
            text.append(":")
            text.append(render_facility_audit(facility))

        text.append("办公室", style="bold")
        text.append(":")
        text.append(render_facility_audit(audit.hire))

        text.append("会客室", style="bold")
        text.append(":")
        text.append(render_facility_audit(audit.meeting))

        for facility in audit.dormitories:
            text.append("宿舍", style="bold")
            text.append(":")
            text.append(render_facility_audit(facility))
        text.remove_suffix("\n")

        panel = Panel(text, title="排班表检查")
        group_elements.append(panel)

    monitor = infrast_assignment.fiammetta_monitor
    if monitor is not None:
        text = Text()

        for operator in monitor.related_operators:
            text.append_text(render_stationed_operator(operator))
            text.append("\n")

        if monitor.fiammetta is not None and monitor.fiammetta_recover_at is not None:
            text.append(render_stationed_operator(monitor.fiammetta))
            text.append(" (预计")
            text.append_text(render_timestamp(monitor.fiammetta_recover_at))
            text.append("回满)\n")

        if monitor.missing_operators:
            text.append("未找到的菲亚梅塔相关干员", style="yellow bold")
            text.append(":")
            for operator_name in monitor.missing_operators:
                text.append(" ")
                text.append(operator_name, style="red bold")

        text.remove_suffix("\n")
        panel = Panel(text, title="菲亚梅塔监控")
        group_elements.append(panel)

    return Group(*group_elements)


__all__ = ["module_entry"]
