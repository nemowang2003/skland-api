from dataclasses import dataclass

from skland_api.models import CharacterInfo


@dataclass(frozen=True, kw_only=True, slots=True)
class Profile:
    nickname: str
    suffix: str


def main(character_info: CharacterInfo, config: dict | None) -> Profile:
    name = character_info.player_info["status"]["name"]
    nickname, suffix = name.rsplit("#", maxsplit=1)

    return Profile(
        nickname=nickname,
        suffix=suffix,
    )
