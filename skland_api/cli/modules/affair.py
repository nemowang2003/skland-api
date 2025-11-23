from skland_api import CharacterInfo
from skland_api.cli.utils import (
    display_timestamp,
    display_capacity_or_progress,
    formatter,
)


def main(character_info: CharacterInfo, config: dict | None):
    with formatter.ready():
        data = character_info.player_info["campaign"]["reward"]
        current = data["current"]
        total = data["total"]
        formatter.write_yellow_bold("剿灭作战进度", suffix=": ")
        formatter.writeline(display_capacity_or_progress(current, total, progress=True))

        data = character_info.player_info["tower"]["reward"]
        formatter.write_yellow_bold("保全派驻进度", suffix=": ")
        higher = data["higherItem"]
        current = higher["current"]
        total = higher["total"]
        formatter.write(
            display_capacity_or_progress(current, total, progress=True),
            ", ",
        )

        lower = data["lowerItem"]
        current = lower["current"]
        total = lower["total"]
        formatter.write(
            display_capacity_or_progress(current, total, progress=True),
            " ",
        )

        term_end = display_timestamp(data["termTs"])
        formatter.writeline(f"({term_end}周期结束)")
