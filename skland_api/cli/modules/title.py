from ..character_info import CharacterInfo
from .. import utils

import wcwidth


def handle(character_info: CharacterInfo):
    data = character_info.player_info
    data = data["status"]
    name = data["name"]
    left, right = name.rsplit("#", maxsplit=1)
    print(utils.green_bold(left), utils.green_bold(right), sep="#")

    update_time = data["storeTs"]
    msg = "".join(["更新于", utils.display_time(update_time)])
    print(msg)

    print("-" * wcwidth.wcswidth(msg))
