from skland_api import CharacterInfo
from skland_api.cli.utils import Formatter, display_capacity_or_progress


def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        mission = character_info.player_info["routine"]
        daily = mission["daily"]
        formatter.write_yellow_bold("日常任务进度", suffix=": ")
        current = daily["current"]
        total = daily["total"]
        formatter.writeline(display_capacity_or_progress(current, total, progress=True))

        weekly = mission["weekly"]
        formatter.write_yellow_bold("周常任务进度", suffix=": ")
        current = weekly["current"]
        total = weekly["total"]
        formatter.writeline(display_capacity_or_progress(current, total, progress=True))
