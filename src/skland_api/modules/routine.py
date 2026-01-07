from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from skland_api.models import CharacterInfo, Progress, TimeStamp

UTC8 = timezone(timedelta(hours=8))


@dataclass(frozen=True, kw_only=True, slots=True)
class RoutineStatus:
    """
    annihilation: 剿灭作战进度
    sss_instrument: 保全派驻数据增补仪获取进度
    sss_component: 保全派驻数据增补条获取进度
    sss_end: 保全派驻周期结束时间
    """

    annihilation: Progress
    annihilation_reset_at: TimeStamp
    sss_instrument: Progress
    sss_component: Progress
    sss_reset_at: TimeStamp


def get_annihilation_end_time() -> TimeStamp:
    now = datetime.now(tz=UTC8)
    target_date = now.date()

    # weekday()返回值规定 周一: 0, 周二: 1 ...
    today = now.weekday()

    # 跳转相应天数
    if today > 0 or now.hour >= 4:
        target_date += timedelta(days=7 - today)

    target_time = datetime.combine(target_date, time(hour=4), tzinfo=UTC8)

    return TimeStamp(int(target_time.timestamp()))


def main(character_info: CharacterInfo, config: dict | None) -> RoutineStatus:
    data = character_info.player_info["campaign"]["reward"]
    annihilation = Progress(data["current"], data["total"])

    data = character_info.player_info["tower"]["reward"]
    instrument = data["higherItem"]
    sss_instrument = Progress(instrument["current"], instrument["total"])

    component = data["lowerItem"]
    sss_component = Progress(component["current"], component["total"])

    sss_reset_at = TimeStamp(data["termTs"])

    return RoutineStatus(
        annihilation=annihilation,
        annihilation_reset_at=get_annihilation_end_time(),
        sss_instrument=sss_instrument,
        sss_component=sss_component,
        sss_reset_at=sss_reset_at,
    )
