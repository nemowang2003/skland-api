from ..character_info import CharacterInfo
from .. import utils


def handle(character_info: CharacterInfo):
    data = character_info.player_info["building"]
    print(utils.yellow_bold("基建概览"))
    print(
        "  ",
        utils.yellow_bold("疲劳干员"),
        ": ",
        # ", ".join(utils.red_bold(character_info.operator_mapping[char[]]) for char in data["tiredChars"])
        ", ".join(
            utils.red_bold(character_info.operator_mapping[char["charId"]])
            for char in data["tiredChars"]
        )
        or utils.green_bold("无"),
        sep="",
    )
