from ..character_info import CharacterInfo
from .. import utils


def handle(character_info: CharacterInfo):
    data = character_info.player_info["campaign"]["reward"]
    current = data["current"]
    total = data["total"]
    msg = utils.yellow_bold("剿灭作战进度") + ": "
    if current < total:
        color = utils.red_bold
    else:
        color = utils.green_bold
    msg += color(f"{current}/{total}")
    print(msg)

    data = character_info.player_info["tower"]["reward"]
    msg = utils.yellow_bold("保全派驻进度") + ": "
    higher = data["higherItem"]
    if (current := higher["current"]) < (total := higher["total"]):
        color = utils.red_bold
    else:
        color = utils.green_bold
    msg += color(f"{current}/{total}") + ", "
    lower = data["lowerItem"]
    if (current := lower["current"]) < (total := lower["total"]):
        color = utils.red_bold
    else:
        color = utils.green_bold
    msg += color(f"{current}/{total}")

    term_end = utils.display_time(data["termTs"])
    msg += f" ({term_end}周期结束)"
    print(msg)
