from ..character_info import CharacterInfo
from .. import utils

from datetime import datetime


def handle(character_info: CharacterInfo):
    msg = utils.yellow_bold("每日签到") + ": "
    daily_sign_info = character_info.api.daily_sign_info(character_info.uid)
    records = daily_sign_info["records"]
    if (
        records
        and datetime.fromtimestamp(int(records[-1]["ts"])).day == datetime.now().day
    ):
        msg += "今日已签到"
    else:
        awards = character_info.api.do_daily_sign(character_info.uid)
        msg += utils.green_bold("签到成功") + ": "
        msg += ", ".join(
            f"【{award['resource']['name']}】×{award['count']}" for award in awards
        )
    print(msg)
