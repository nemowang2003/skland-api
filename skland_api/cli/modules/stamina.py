from skland_api import CharacterInfo
from skland_api.cli.utils import (
    Formatter,
    display_timestamp,
    display_capacity_or_progress,
)


def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        data = character_info.player_info["status"]["ap"]

        now = character_info.player_info["currentTs"]
        since_last_add = now - data["lastApAddTime"]
        current = data["current"]
        formatter.write_yellow_bold("预计当前理智", suffix=": ")
        total = data["max"]
        # 6 * 60 means 6 minutes for 1 stamina
        current = min(total, current + since_last_add // (6 * 60))
        formatter.writeline(display_capacity_or_progress(current, total, capacity=True))

        recovery_time = data["completeRecoveryTime"]
        formatter.write_yellow_bold("理智回满时间", suffix=": ")
        formatter.writeline(display_timestamp(recovery_time))
