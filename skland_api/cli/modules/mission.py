from ..character_info import CharacterInfo
from .. import utils


def handle(character_info: CharacterInfo):
    mission = character_info.player_info["routine"]

    daily = mission["daily"]
    msg = utils.yellow_bold("日常任务进度") + ": "
    current = daily["current"]
    total = daily["total"]
    if current < total:
        color = utils.red_bold
    else:
        color = utils.green_bold
    msg += color(f"{current}/{total}")
    print(msg)

    weekly = mission["weekly"]
    msg = utils.yellow_bold("周常任务进度") + ": "
    current = weekly["current"]
    total = weekly["total"]
    if current < total:
        color = utils.red_bold
    else:
        color = utils.green_bold
    msg += color(f"{current}/{total}")
    print(msg)
