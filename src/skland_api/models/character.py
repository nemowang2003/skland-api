import asyncio
import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from skland_api.api import SklandApi

from . import constants


@dataclass(frozen=True, kw_only=True, slots=True)
class OperatorInfo:
    """
    evolve: 精英化等级 {0, 1, 2}
    master_levels: 专精等级 {0, 1, 2, 3}, 列表长度为技能数量
    """

    evolve: int
    mastery_levels: list[int]


# Cannot use frozen=True and slots=True because of cached_property
@dataclass(kw_only=True)
class CharacterInfo:
    name: str
    api: SklandApi
    uid: str
    cultivate: dict
    player_info: dict

    @cached_property
    def operator_name_mapping(self) -> dict[str, str]:
        """
        char_id -> display_name
        """
        return {entry["id"]: entry["name"] for entry in self.player_info["charInfoMap"].values()}

    @cached_property
    def operator_name_mapping_with_fix(self) -> dict[str, str]:
        """
        char_id -> display_name
        """
        return self.operator_name_mapping | constants.OPERATOR_NAME_MAPPING_FIX

    @cached_property
    def operators(self) -> dict[str, OperatorInfo]:
        """
        char_id -> OperatorInfo
        """
        return {
            entry["id"]: OperatorInfo(
                evolve=entry["evolvePhase"],
                mastery_levels=[skill["level"] for skill in entry["skills"]],
            )
            for entry in self.cultivate["characters"]
        }

    @cached_property
    def depot(self) -> dict[str, int]:
        """
        display_name -> count
        """
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
