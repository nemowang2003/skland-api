from rich.text import Text

from skland_api.modules.checkin import CheckinResult
from skland_api.modules.checkin import main as module_entry

from . import render


@render.register
def render_checkin_result(checkin_result: CheckinResult) -> Text:
    text = Text().append("每日签到", style="yellow bold").append(": ")
    if checkin_result.already_checked_in:
        return text.append("今日已签到", style="green bold")
    awards = ", ".join(f"【{award.name}】×{award.count}" for award in checkin_result.awards)
    return text.append("签到成功", style="green bold").append(awards)


__all__ = ["module_entry"]
