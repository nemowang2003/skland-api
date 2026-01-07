from dataclasses import dataclass

from skland_api.models import CharacterInfo, TimeStamp


@dataclass(frozen=True, kw_only=True, slots=True)
class UpdateStatus:
    last_update_at: TimeStamp


def main(character_info: CharacterInfo, config: dict | None) -> UpdateStatus:
    return UpdateStatus(last_update_at=TimeStamp(character_info.player_info["status"]["storeTs"]))
