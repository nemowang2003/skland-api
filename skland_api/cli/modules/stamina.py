from ..character_info import CharacterInfo
from .. import utils


def handle(character_info: CharacterInfo):
    data = character_info.player_info
    now = data["currentTs"]
    data = data["status"]["ap"]

    since_last_add = now - data["lastApAddTime"]
    current = data["current"]
    capacity = data["max"]
    # 6 * 60 means 6 minutes for 1 stamina
    current = min(capacity, current + since_last_add // (6 * 60))

    if current < capacity:
        color = utils.green_bold
    else:
        color = utils.red_bold
    print(
        utils.yellow_bold("预计当前理智"),
        ": ",
        color(f"{current}/{capacity}"),
        sep="",
    )

    recovery_time = data["completeRecoveryTime"]
    print(
        utils.yellow_bold("理智回满时间"),
        ": ",
        utils.display_time(recovery_time),
        sep="",
    )
