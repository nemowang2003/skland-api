from collections import UserDict, UserList
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from itertools import chain, permutations
from typing import Self

from loguru import logger

from skland_api.models import CharacterInfo, TimeStamp

MORALE_DIVIDOR = 360000
FULL_MORALE = 24
FIAMMETTA_RECOVER_PER_SECOND = 2 / 3600


@dataclass(frozen=True, kw_only=True, slots=True)
class StationedOperatorInfo:
    name: str
    morale: float

    @classmethod
    def from_skland_data(cls, data: dict, name_mapping: dict[str, str]) -> Self:
        return cls(
            name=name_mapping[data["charId"]],
            morale=data["ap"] / MORALE_DIVIDOR,
        )


class FacilityPresence(UserList[StationedOperatorInfo]):
    @classmethod
    def from_skland_data(cls, data: list | dict, name_mapping: dict[str, str]) -> list[Self]:
        if isinstance(data, dict):
            data = [data]
        return [
            cls(
                [
                    StationedOperatorInfo.from_skland_data(char, name_mapping)
                    for char in segment["chars"]
                ]
            )
            for segment in data
        ]


class FacilityEnum(StrEnum):
    control = "控制中枢"
    power = "发电站"
    trading = "贸易站"
    manufacture = "制造站"
    hire = "办公室"
    meeting = "会客室"
    dormitory = "宿舍"


maa_entry: dict[FacilityEnum, str] = {e: e.name for e in FacilityEnum}
skland_entry: dict[FacilityEnum, str] = maa_entry | {
    FacilityEnum.power: "powers",
    FacilityEnum.trading: "tradings",
    FacilityEnum.manufacture: "manufactures",
    FacilityEnum.dormitory: "dormitories",
}


class InfrastBase[T](UserDict[FacilityEnum, list[T]]):
    def iter_facilities(self) -> Iterator[tuple[FacilityEnum, T]]:
        for k, vs in self.items():
            for v in vs:
                yield k, v


class InfrastPresence(InfrastBase[FacilityPresence]):
    @classmethod
    def from_character_info(cls, character_info: CharacterInfo) -> Self:
        data = character_info.player_info["building"]
        mapping = character_info.operator_name_mapping
        return cls(
            {
                e: FacilityPresence.from_skland_data(data[skland_entry[e]], mapping)
                for e in FacilityEnum
            }
        )


@dataclass(order=True, slots=True)
class Cost:
    x: float = 0
    y: float = 0

    def __iadd__(self, other: Cost) -> Self:
        self.x += other.x
        self.y += other.y
        return self


def cost(roster: FacilityRoster, presence: FacilityPresence) -> Cost:
    expected = set(roster)
    actual = set(operator.name for operator in presence)
    return Cost(len(expected ^ actual), -len(expected & actual))


def align_facilities(
    rosters: list[FacilityRoster], presences: list[FacilityPresence]
) -> Iterator[tuple[FacilityRoster, FacilityPresence]]:
    # perm 是一个 0 到 len(rosters)-1 的排列
    # perm 指的是 rosters[k] 对应 presences[perm[k]]
    best_cost = Cost(float("inf"), float("inf"))
    for perm in permutations(range(len(rosters))):
        current_cost = Cost()
        for k, v in enumerate(perm):
            current_cost += cost(rosters[k], presences[v])
        if current_cost < best_cost:
            best_cost = current_cost
            best_perm = perm

    return zip(rosters, [presences[v] for v in best_perm])


@dataclass(frozen=True, kw_only=True, slots=True)
class FacilityAudit:
    missing: list[str]
    present: list[StationedOperatorInfo]
    unexpected: list[StationedOperatorInfo]

    @classmethod
    def from_facility(
        cls, rosters: list[FacilityRoster], presences: list[FacilityPresence]
    ) -> list[Self]:
        return [
            cls(
                missing=[
                    operator
                    for operator in roster
                    if operator not in (operator.name for operator in presence)
                ],
                present=[operator for operator in presence if operator.name in roster],
                unexpected=[operator for operator in presence if operator.name not in roster],
            )
            for roster, presence in align_facilities(rosters, presences)
        ]


class FacilityRoster(UserList[str]):
    @classmethod
    def from_maa_roster(cls, data: dict) -> list[Self]:
        return [cls(segment["operators"]) for segment in data]


class InfrastRoster(InfrastBase[FacilityRoster]):
    @classmethod
    def from_maa_roster(cls, config: dict) -> Self:
        return cls({e: FacilityRoster.from_maa_roster(config[maa_entry[e]]) for e in FacilityEnum})


class InfrastAudit(InfrastBase[FacilityAudit]):
    @classmethod
    def new(cls, infrast_presence: InfrastPresence, active_roster: InfrastRoster) -> Self:
        return cls(
            {
                e: FacilityAudit.from_facility(active_roster[e], infrast_presence[e])
                for e in FacilityEnum
            }
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class FiammettaMonitor:
    related_operators: list[StationedOperatorInfo]
    missing_operators: set[str]
    fiammetta: StationedOperatorInfo | None
    fiammetta_recover_at: TimeStamp | None

    @classmethod
    def new(
        cls, infrast_presence: InfrastPresence, fiammetta_releated: set[str], update_time: int
    ) -> Self:
        if "菲亚梅塔" in fiammetta_releated:
            logger.warning("'菲亚梅塔'在'菲亚梅塔'换班对象中，请检查排班表是否正确")
            fiammetta_releated.remove("菲亚梅塔")
        present = []
        fiammetta = None
        fiammetta_recover_at = None
        for operator in chain.from_iterable(v for _, v in infrast_presence.iter_facilities()):
            if operator.name in fiammetta_releated:
                present.append(operator)
                fiammetta_releated.remove(operator.name)
            elif operator.name == "菲亚梅塔":
                fiammetta = operator
        if fiammetta is not None:
            fiammetta_recover_at = TimeStamp(
                update_time + int((FULL_MORALE - fiammetta.morale) / FIAMMETTA_RECOVER_PER_SECOND)
            )
        else:
            fiammetta_releated.add("菲亚梅塔")

        return cls(
            related_operators=present,
            missing_operators=fiammetta_releated,
            fiammetta=fiammetta,
            fiammetta_recover_at=fiammetta_recover_at,
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class InfrastAssignmentReport:
    audit: InfrastAudit | None = None
    fiammetta_monitor: FiammettaMonitor | None = None


def main(character_info: CharacterInfo, config: dict | None) -> InfrastAssignmentReport:
    if config is None or (path := config.get("path")) is None:
        logger.warning(f"no path configured for {character_info.name!r}")
        return InfrastAssignmentReport()

    from pathlib import Path

    file = Path(path)
    if not file.exists():
        logger.warning(f"{character_info.name!r} 的排班表路径 {path!r} 不存在")
        return InfrastAssignmentReport()

    import json
    from datetime import datetime

    update_time = character_info.player_info["status"]["storeTs"]
    update_time_str = datetime.fromtimestamp(update_time).strftime("%H:%M")

    with file.open(mode="r", encoding="utf-8") as fp:
        roster_data = json.load(fp)

    fiammetta_releated = set()
    active_rosters = []
    for roster in roster_data["plans"]:
        if (fiammetta := roster.get("Fiammetta")) is not None:
            if fiammetta["enable"]:
                fiammetta_releated.add(fiammetta["target"])

        if any(start < update_time_str < end for start, end in roster["period"]):
            active_rosters.append(roster)
    infrast_presence = InfrastPresence.from_character_info(character_info)

    if len(active_rosters) == 0:
        logger.warning(f"{character_info.name!r} 没有适用于此时的排班计划")
        audit = None
    elif len(active_rosters) > 1:
        logger.warning(f"{character_info.name!r} 有 {len(active_rosters)} 个适用于此时的排班计划")
        audit = None
    else:
        audit = InfrastAudit.new(
            infrast_presence, InfrastRoster.from_maa_roster(active_rosters[0]["rooms"])
        )

    if fiammetta_releated:
        fiammetta_monitor = FiammettaMonitor.new(infrast_presence, fiammetta_releated, update_time)
    else:
        fiammetta_monitor = None

    return InfrastAssignmentReport(
        audit=audit,
        fiammetta_monitor=fiammetta_monitor,
    )
