from dataclasses import dataclass

from skland_api.models import CharacterInfo, Progress, TimeStamp


@dataclass(frozen=True, kw_only=True, slots=True)
class RoutineStatus:
    """
    annihilation: 剿灭作战进度
    sss_instrument: 保全派驻数据增补仪获取进度
    sss_component: 保全派驻数据增补条获取进度
    sss_end: 保全派驻周期结束时间
    """

    annihilation: Progress
    sss_instrument: Progress
    sss_component: Progress
    sss_reset_at: TimeStamp


def main(character_info: CharacterInfo, config: dict | None) -> RoutineStatus:
    data = character_info.player_info["campaign"]["reward"]
    annihilation = Progress(data["current"], data["total"])

    data = character_info.player_info["tower"]["reward"]
    higher = data["higherItem"]
    sss_instrument = Progress(higher["current"], higher["total"])

    lower = data["lowerItem"]
    sss_component = Progress(lower["current"], lower["total"])

    sss_reset_at = TimeStamp(data["termTs"])

    return RoutineStatus(
        annihilation=annihilation,
        sss_instrument=sss_instrument,
        sss_component=sss_component,
        sss_reset_at=sss_reset_at,
    )
