from datetime import datetime

from skland_api import CharacterInfo
from skland_api.cli.utils import Formatter


async def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        daily_sign_info = await character_info.api.daily_sign_info(character_info.uid)

        formatter.write_yellow_bold("每日签到", suffix=": ")
        records = daily_sign_info["records"]
        if records and datetime.fromtimestamp(int(records[-1]["ts"])).day == datetime.now().day:
            formatter.writeline("今日已签到")
        else:
            awards = await character_info.api.do_daily_sign(character_info.uid)
            formatter.write_green_bold("签到成功", suffix=": ")
            formatter.writeline(
                ", ".join(f"【{award['resource']['name']}】×{award['count']}" for award in awards)
            )
