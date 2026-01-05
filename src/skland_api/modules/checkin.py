from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from skland_api.models import CharacterInfo

UTC8 = timezone(timedelta(hours=8))


@dataclass(frozen=True, kw_only=True, slots=True)
class CheckinAward:
    name: str
    count: int


@dataclass(frozen=True, kw_only=True, slots=True)
class CheckinResult:
    already_checked_in: bool
    awards: list[CheckinAward] = field(default_factory=list)


async def main(character_info: CharacterInfo, config: dict | None) -> CheckinResult:
    checkin_status = await character_info.api.get_daily_checkin_status(character_info.uid)

    records = checkin_status["records"]
    if records and datetime.fromtimestamp(int(records[-1]["ts"])).day == datetime.now(tz=UTC8).day:
        return CheckinResult(already_checked_in=True)
    awards = await character_info.api.execute_daily_checkin(character_info.uid)
    return CheckinResult(
        already_checked_in=False,
        awards=[
            CheckinAward(name=award["resource"]["name"], count=award["count"]) for award in awards
        ],
    )
