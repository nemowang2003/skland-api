from skland_api import CharacterInfo
from skland_api.cli.utils import (
    Formatter,
    display_capacity_or_progress,
    display_timestamp,
)

IS_RECRUITING = 2
MAX_REFRESH_COUNT = 3


def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        data = character_info.player_info
        now = data["currentTs"]
        progress_data = data["recruit"]

        formatter.write_yellow_bold("公招概览", suffix="\n")
        with formatter.indent():
            for index, progress in enumerate(progress_data, start=1):
                formatter.write_yellow_bold(f"栏位{index}", suffix=": ")
                state = progress["state"]
                if state == IS_RECRUITING:  # 2 for recruiting
                    end_time = progress["finishTs"]
                    if end_time < now:
                        formatter.write_green_bold("招募完毕", suffix="\n")
                    else:
                        formatter.writeline(f"{display_timestamp(end_time)}招募完毕")
                else:
                    formatter.write_green_bold("空闲", suffix="\n")

            formatter.write_yellow_bold("刷新次数", suffix=": ")
            refresh_data = data["building"]["hire"]
            refresh_count = refresh_data["refreshCount"]
            refresh_time = refresh_data["completeWorkTime"]
            if refresh_time < now:
                refresh_count += 1
            formatter.write(
                display_capacity_or_progress(refresh_count, MAX_REFRESH_COUNT, capacity=True),
                f" ({display_timestamp(refresh_time)}刷新)",
            )
