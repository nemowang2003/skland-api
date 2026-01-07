from collections import UserList
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import permutations
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
    def from_skland_data(cls, data: dict, name_mapping: dict[str, str]) -> Self:
        return cls(
            [StationedOperatorInfo.from_skland_data(char, name_mapping) for char in data["chars"]]
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class InfrastPresence:
    control: FacilityPresence
    powers: list[FacilityPresence]
    tradings: list[FacilityPresence]
    manufactures: list[FacilityPresence]
    hire: FacilityPresence
    meeting: FacilityPresence
    dormitories: list[FacilityPresence]

    def __iter__(self) -> Iterator[StationedOperatorInfo]:
        yield from self.control
        for power in self.powers:
            yield from power
        for trading in self.tradings:
            yield from trading
        for manufacture in self.manufactures:
            yield from manufacture
        yield from self.hire
        yield from self.meeting
        for dormitory in self.dormitories:
            yield from dormitory

    @classmethod
    def from_character_info(cls, character_info: CharacterInfo) -> Self:
        data = character_info.player_info["building"]
        return cls(
            control=FacilityPresence.from_skland_data(
                data["control"], character_info.operator_name_mapping
            ),
            powers=[
                FacilityPresence.from_skland_data(power, character_info.operator_name_mapping)
                for power in data["powers"]
            ],
            tradings=[
                FacilityPresence.from_skland_data(trading, character_info.operator_name_mapping)
                for trading in data["tradings"]
            ],
            manufactures=[
                FacilityPresence.from_skland_data(manufacture, character_info.operator_name_mapping)
                for manufacture in data["manufactures"]
            ],
            hire=FacilityPresence.from_skland_data(
                data["hire"], character_info.operator_name_mapping
            ),
            meeting=FacilityPresence.from_skland_data(
                data["meeting"], character_info.operator_name_mapping
            ),
            dormitories=[
                FacilityPresence.from_skland_data(dormitory, character_info.operator_name_mapping)
                for dormitory in data["dormitories"]
            ],
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class FacilityAudit:
    missing: list[str]
    present: list[StationedOperatorInfo]
    unexpected: list[StationedOperatorInfo]

    @classmethod
    def from_facility(cls, roster: FacilityRoster, presence: FacilityPresence) -> Self:
        expected = set(roster)
        actual = set(operator.name for operator in presence)
        # 保留在 roster 和 presence 中的顺序
        return cls(
            missing=[operator for operator in roster if operator not in actual],
            present=[operator for operator in presence if operator.name in expected],
            unexpected=[operator for operator in presence if operator.name not in expected],
        )


class FacilityRoster(UserList[str]):
    @classmethod
    def from_maa_roster(cls, config: dict) -> Self:
        return cls(config["operators"])


@dataclass(frozen=True, kw_only=True, slots=True)
class InfrastRoster:
    control: FacilityRoster
    powers: list[FacilityRoster]
    tradings: list[FacilityRoster]
    manufactures: list[FacilityRoster]
    hire: FacilityRoster
    meeting: FacilityRoster
    dormitories: list[FacilityRoster]

    @classmethod
    def from_maa_roster(cls, config: dict) -> Self:
        return cls(
            control=FacilityRoster.from_maa_roster(config["control"][0]),
            powers=[FacilityRoster.from_maa_roster(power) for power in config["power"]],
            tradings=[FacilityRoster.from_maa_roster(trading) for trading in config["trading"]],
            manufactures=[
                FacilityRoster.from_maa_roster(manufacture) for manufacture in config["manufacture"]
            ],
            hire=FacilityRoster.from_maa_roster(config["hire"][0]),
            meeting=FacilityRoster.from_maa_roster(config["meeting"][0]),
            dormitories=[
                FacilityRoster.from_maa_roster(dormitory) for dormitory in config["dormitory"]
            ],
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
class InfrastAudit:
    control: FacilityAudit
    powers: list[FacilityAudit]
    tradings: list[FacilityAudit]
    manufactures: list[FacilityAudit]
    hire: FacilityAudit
    meeting: FacilityAudit
    dormitories: list[FacilityAudit]

    @classmethod
    def new(cls, infrast_presence: InfrastPresence, active_roster: InfrastRoster) -> Self:
        return cls(
            control=FacilityAudit.from_facility(active_roster.control, infrast_presence.control),
            powers=[
                FacilityAudit.from_facility(roster, presence)
                for roster, presence in align_facilities(
                    active_roster.powers, infrast_presence.powers
                )
            ],
            tradings=[
                FacilityAudit.from_facility(roster, presence)
                for roster, presence in align_facilities(
                    active_roster.tradings, infrast_presence.tradings
                )
            ],
            manufactures=[
                FacilityAudit.from_facility(roster, presence)
                for roster, presence in align_facilities(
                    active_roster.manufactures, infrast_presence.manufactures
                )
            ],
            hire=FacilityAudit.from_facility(active_roster.hire, infrast_presence.hire),
            meeting=FacilityAudit.from_facility(active_roster.meeting, infrast_presence.meeting),
            dormitories=[
                FacilityAudit.from_facility(roster, presence)
                for roster, presence in align_facilities(
                    active_roster.dormitories, infrast_presence.dormitories
                )
            ],
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
        for operator in infrast_presence:
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
    if config is None or (path := config.get(character_info.name)) is None:
        logger.warning(f"no path configured for {character_info.name!r}")
        return InfrastAssignmentReport()

    from pathlib import Path

    file = Path(path)
    if not file.exists():
        logger.warning(f"invalid path {path!r} for {character_info.name!r}")
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
        logger.warning(f"no active roster for {character_info.name!r}")
        audit = None
    elif len(active_rosters) > 1:
        logger.warning(f"multiple active rosters for {character_info.name!r}")
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
