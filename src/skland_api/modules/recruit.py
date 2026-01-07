from dataclasses import dataclass
from typing import Self

from skland_api.models import Capacity, CharacterInfo, Duration, TimeStamp

IS_RECRUITING = 2
MAX_REFRESH_COUNT = 3


@dataclass(frozen=True, kw_only=True, slots=True)
class RecruitStatus:
    is_idle: bool
    finish_at: TimeStamp | None = None

    @classmethod
    def from_skland_data(cls, data: dict) -> Self:
        is_idle = data["state"] != IS_RECRUITING
        if is_idle:
            return cls(is_idle=True)
        return cls(
            is_idle=False,
            finish_at=data["finishTs"],
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class RecruitOverview:
    recruits: list[RecruitStatus]
    refresh: Capacity
    refresh_at: TimeStamp | None = None


def main(character_info: CharacterInfo, config: dict | None) -> RecruitOverview:
    recruits = [
        RecruitStatus.from_skland_data(item) for item in character_info.player_info["recruit"]
    ]
    refresh_data = character_info.player_info["building"]["hire"]
    current_refresh = refresh_data["refreshCount"]
    if current_refresh == MAX_REFRESH_COUNT:
        refresh_at = None
    else:
        refresh_at = TimeStamp(refresh_data["completeWorkTime"])
        if Duration.from_now(refresh_at) < 0:
            current_refresh += 1

    return RecruitOverview(
        recruits=recruits,
        refresh=Capacity(current_refresh, MAX_REFRESH_COUNT),
        refresh_at=refresh_at,
    )
