import asyncio
import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from . import constants
from .api import SklandApi


# Cannot use frozen=True and slots=True because of cached_property
@dataclass(kw_only=True)
class CharacterInfo:
    name: str
    api: SklandApi
    uid: str
    cultivate: dict
    player_info: dict

    @cached_property
    def operator_mapping(self) -> dict:
        return {
            entry["id"]: entry["name"] for entry in self.player_info["charInfoMap"].values()
        } | constants.OPERATOR_MAPPING_FIX

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

    def dump_to(self, cache_path: Path) -> None:
        file = cache_path / f"{self.name}-{self.uid}-player_info.json"
        with file.open(mode="w", encoding="utf-8") as fp:
            json.dump(self.player_info, fp, ensure_ascii=False, indent=2)
        file = cache_path / f"{self.name}-{self.uid}-cultivate.json"
        with file.open(mode="w", encoding="utf-8") as fp:
            json.dump(self.cultivate, fp, ensure_ascii=False, indent=2)


class CharacterInfoLoader:
    def __init__(self, name: str, api: SklandApi, character: dict):
        self.name = name
        self.api = api
        self.uid = character["uid"]

    async def only_load_cultivate(self) -> CharacterInfo:
        cultivate = await self.api.cultivate(self.uid)
        return CharacterInfo(
            name=self.name,
            api=self.api,
            uid=self.uid,
            cultivate=cultivate,
            player_info={},
        )

    async def only_load_player_info(self) -> CharacterInfo:
        player_info = await self.api.player_info(self.uid)
        return CharacterInfo(
            name=self.name,
            api=self.api,
            uid=self.uid,
            cultivate={},
            player_info=player_info,
        )

    async def full_load(self) -> CharacterInfo:
        cultivate, player_info = await asyncio.gather(
            self.api.cultivate(self.uid),
            self.api.player_info(self.uid),
        )
        return CharacterInfo(
            name=self.name,
            api=self.api,
            uid=self.uid,
            cultivate=cultivate,
            player_info=player_info,
        )
