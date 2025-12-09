import wcwidth

from skland_api import CharacterInfo
from skland_api.cli.utils import Formatter, display_timestamp


def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        data = character_info.player_info["status"]

        name = data["name"]
        left, right = name.rsplit("#", maxsplit=1)
        formatter.write_green_bold(left, suffix="#")
        formatter.write_green_bold(right, suffix="\n")

        update_time = data["storeTs"]
        msg = f"更新于{display_timestamp(update_time)}"
        formatter.writeline(msg)
        formatter.writeline("-" * wcwidth.wcswidth(msg))
