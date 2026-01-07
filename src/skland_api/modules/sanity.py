from dataclasses import dataclass

from skland_api.models import Capacity, CharacterInfo, Duration, TimeStamp

SANITY_RECOVER_PER_SECOND = 1 / 6 / 60


@dataclass(frozen=True, kw_only=True, slots=True)
class SanityStatus:
    sanity: Capacity
    full_at: TimeStamp


def main(character_info: CharacterInfo, config: dict | None) -> SanityStatus:
    data = character_info.player_info["status"]["ap"]

    since_last_add = Duration.to_now(data["lastApAddTime"])
    current = data["current"]
    total = data["max"]

    # 当前理智超限时不计算自更新以来的回复值
    if current < total:
        current = min(total, int(current + since_last_add * SANITY_RECOVER_PER_SECOND))
    # TODO: 确认当前理智已超限时该字段是否有意义
    full_at = TimeStamp(data["completeRecoveryTime"])

    return SanityStatus(
        sanity=Capacity(current, total),
        full_at=full_at,
    )
