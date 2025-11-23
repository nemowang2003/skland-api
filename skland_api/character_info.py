from .api import SklandApi
from . import constants

from functools import cached_property
from pathlib import Path


class CharacterInfo:
    def __init__(self, name: str, api: SklandApi, character: dict):
        self.name = name
        self.api = api
        self.uid = character["uid"]
        self.game_id = character["nickName"]

    @cached_property
    def player_info(self) -> dict:
        player_info = self.api.player_info(self.uid)
        return player_info

    @cached_property
    def operator_mapping(self) -> dict:
        return {
            entry["id"]: entry["name"]
            for entry in self.player_info["charInfoMap"].values()
        } | constants.OPERATOR_MAPPING_FIX

    @cached_property
    def cultivate(self) -> dict:
        cultivate = self.api.cultivate(self.uid)
        return cultivate

    @cached_property
    def operators(self) -> dict:
        return {
            self.operator_mapping[entry["id"]]: {
                "evolve": entry["evolvePhase"],
                "skills": [skill["level"] for skill in entry["skills"]],
            }
            for entry in self.cultivate["characters"]
        }

    @cached_property
    def item_mapping(self) -> dict:
        return {
            constants.ITEM_MAPPING[entry["id"]]: entry["count"]
            for entry in self.cultivate["items"]
            if entry["id"] in constants.ITEM_MAPPING
        }

    def dump(self, cache_path: Path) -> None:
        import json

        file = cache_path / f"{self.name}-{self.uid}-player_info.json"
        with file.open(mode="w", encoding="utf-8") as fp:
            json.dump(self.player_info, fp, ensure_ascii=False, indent=2)
        file = cache_path / f"{self.name}-{self.uid}-cultivate.json"
        with file.open(mode="w", encoding="utf-8") as fp:
            json.dump(self.cultivate, fp, ensure_ascii=False, indent=2)
