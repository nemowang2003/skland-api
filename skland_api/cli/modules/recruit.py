from ..character_info import CharacterInfo
from .. import utils


def handle(character_info: CharacterInfo):
    data = character_info.player_info
    now = data["currentTs"]
    progress_data = data["recruit"]
    for index, progress in enumerate(progress_data, start=1):
        state = progress["state"]
        if state == 2:  # 2 for recruiting
            end_time = progress["finishTs"]
            if end_time < now:
                msg = utils.green_bold("招募完毕")
            else:
                msg = utils.display_time(end_time) + "招募完毕"
        else:
            msg = utils.green_bold("空闲")
        print(
            utils.yellow_bold(f"公开招募栏位{index}"),
            ": ",
            msg,
            sep="",
        )

    refresh_data = data["building"]["hire"]
    refresh_count = refresh_data["refreshCount"]

    refresh_time = refresh_data["completeWorkTime"]
    if refresh_time < now:
        refresh_count += 1
    color = utils.green_bold if refresh_count < 3 else utils.red_bold
    msg = color(f"{refresh_count}/3") + f" ({utils.display_time(refresh_time)}刷新)"
    print(
        utils.yellow_bold("公开招募刷新次数"),
        ": ",
        msg,
        sep="",
    )
