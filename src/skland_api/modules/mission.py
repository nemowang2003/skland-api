from dataclasses import dataclass

from skland_api.models import CharacterInfo, Progress


@dataclass(frozen=True, kw_only=True, slots=True)
class MissionStatus:
    daily: Progress
    weekly: Progress


def main(character_info: CharacterInfo, config: dict | None) -> MissionStatus:
    data = character_info.player_info["routine"]
    daily_data = data["daily"]
    daily = Progress(daily_data["current"], daily_data["total"])
    weekly_data = data["weekly"]
    weekily = Progress(weekly_data["current"], weekly_data["total"])

    return MissionStatus(
        daily=daily,
        weekly=weekily,
    )
