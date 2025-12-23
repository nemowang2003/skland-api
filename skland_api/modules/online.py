from skland_api import CharacterInfo
from skland_api.cli.utils import Formatter, display_timestamp


def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        formatter.write_yellow_bold("上次在线时间", suffix=": ")
        formatter.writeline(display_timestamp(character_info.player_info["status"]["lastOnlineTs"]))
