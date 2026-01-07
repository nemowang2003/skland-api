from dataclasses import dataclass

from skland_api.models import CharacterInfo, TimeStamp


@dataclass(frozen=True, kw_only=True, slots=True)
class OnlineStatus:
    last_online_at: TimeStamp


def main(character_info: CharacterInfo, config: dict | None) -> OnlineStatus:
    return OnlineStatus(
        last_online_at=TimeStamp(character_info.player_info["status"]["lastOnlineTs"])
    )
