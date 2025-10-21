from ..character_info import CharacterInfo
from .. import utils


def handle(character_info: CharacterInfo):
    print(
        utils.yellow_bold("上次在线时间"),
        ": ",
        utils.display_time(character_info.player_info["status"]["lastOnlineTs"]),
        sep="",
    )
