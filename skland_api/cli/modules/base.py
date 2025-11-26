from skland_api import CharacterInfo
from skland_api.cli.utils import (
    Formatter,
    display_capacity_or_progress,
    display_remain_seconds,
    display_timestamp,
)

from itertools import permutations
from typing import Generator

import click
import logging
import time

logger = logging.getLogger(__name__)

TOTAL_TRAIN_POINT = 30000
STAMINA_DIVIDOR = 360000
STAMINA_REDLINE = 8
FULL_STAMINA = 24
FIAMMETTA_RECOVER_PER_HOUR = 2

"""
(skland_entry, maa_plan_entry, display_string)
"""
FACILITY_KEYS = (
    ("control", "control", click.style("控制中枢", bold=True)),
    ("powers", "power", click.style("发电站", fg="green", bold=True)),
    ("tradings", "trading", click.style("贸易站", fg="blue", bold=True)),
    ("manufactures", "manufacture", click.style("制造站", fg="yellow", bold=True)),
    ("hire", "hire", click.style("办公室", bold=True)),
    ("meeting", "meeting", click.style("会客室", bold=True)),
    ("dormitories", "dormitory", click.style("宿舍", bold=True)),
)


def iter_operator_from_skland_facility(
    data: dict, entry: str
) -> Generator[dict, None, None]:
    result = data[entry]
    if isinstance(result, list):
        yield from data[entry]
    elif isinstance(result, dict):
        yield data[entry]
    else:
        raise TypeError(f"Unexpected type {type(result)!r}")


type Group = set[str]


def align_group(
    expected: list[Group],
    actual: list[Group],
) -> tuple[list[Group], list[Group]]:
    """
    align_group(expected, actual) -> expected, aligned_actual
    usage:
        expcted, actual = align_group(expected, actual)
        for e, a in zip(expcted, actual):
            missing = e - a
            present = e & a
            unexpected = a - e
    """
    assert (n := len(expected)) == len(actual)

    def cost(e: Group, a: Group) -> tuple[int, int]:
        return len(e ^ a), -len(e & a)

    # perm[k]: expected[k] -> actual[perm[k]]
    perm_it = permutations(range(n))
    best_perm = next(perm_it)
    best_cost = sum(
        (cost(expected[i], actual[best_perm[i]]) for i in range(n)),
        start=(0, 0),
    )
    for perm in perm_it:
        total = sum(
            (cost(expected[i], actual[perm[i]]) for i in range(n)),
            start=(0, 0),
        )
        if total < best_cost:
            best_cost = total
            best_perm = perm

    return expected, [actual[best_perm[i]] for i in range(n)]


def main(character_info: CharacterInfo, config: dict | None):
    with Formatter() as formatter:
        data = character_info.player_info["building"]
        update_time = character_info.player_info["status"]["storeTs"]

        formatter.write_yellow_bold("基建概览", suffix="\n")
        with formatter.indent():
            formatter.write_yellow_bold("预计无人机数量", suffix=": ")
            drone = data["labor"]
            current = drone["value"]
            total = drone["maxValue"]
            remain_seconds = drone["remainSecs"]
            # 无人机的remainSecs数据按照更新时间计算（与专精的remainSecs不同）

            if remain_seconds > 0:
                now = int(time.time())
                approximate_recover_speed = (total - current) / remain_seconds
                remain_seconds = max(remain_seconds + update_time - now, 0)
                current = min(
                    current + int((now - update_time) * approximate_recover_speed),
                    total,
                )

            formatter.write(display_capacity_or_progress(current, total, capacity=True))

            if remain_seconds > 0:
                formatter.write(f" (预计{display_remain_seconds(remain_seconds)}补满)")
            formatter.write("\n")

            formatter.write_yellow_bold("疲劳干员", suffix=":")
            if data["tiredChars"]:
                for char in data["tiredChars"]:
                    formatter.write_red_bold(
                        character_info.operator_mapping[char["charId"]], prefix=" "
                    )
            else:
                formatter.write_green_bold("无", prefix=" ")
            formatter.write("\n")

            formatter.write_yellow_bold("专精状态")
            training = data["training"]
            trainee = training["trainee"]
            if trainee is None or trainee["targetSkill"] == -1:
                formatter.writeline(": 无")
            else:
                with formatter.indent():
                    name = character_info.operator_mapping[trainee["charId"]]
                    skill_id = trainee["targetSkill"]
                    formatter.write_yellow_bold("专精干员", suffix=": ")
                    formatter.writeline(f"{name}({skill_id + 1}技能)")

                    formatter.write_yellow_bold("协助干员", suffix=": ")
                    trainer = training["trainer"]
                    if trainer is None:
                        formatter.write_red_bold("无", suffix="\n")
                    else:
                        name = character_info.operator_mapping[trainer["charId"]]
                        formatter.writeline(name)

                    percentage = int(
                        (TOTAL_TRAIN_POINT - training["remainPoint"] + 1)
                        * 100
                        / TOTAL_TRAIN_POINT
                    )
                    remain_seconds = training["remainSecs"]
                    formatter.write_yellow_bold("专精进度", suffix=": ")
                    formatter.writeline(
                        f"{percentage}% ({display_remain_seconds(remain_seconds)}完成)"
                    )
                    formatter.write_style(
                        "TODO: 适配不同专精等级，根据当前时间计算进度",
                        suffix="\n",
                        fg="cyan",
                        bold=True,
                    )

            if config is None or (path := config.get(character_info.name)) is None:
                return
            from pathlib import Path

            file = Path(path)
            if not file.exists():
                logging.warning(f"invalid path {path!r} for {character_info.name!r}")
                return

            from datetime import datetime
            import json

            formatter.write_yellow_bold("排班表检查")
            update_time_str = datetime.fromtimestamp(update_time).strftime("%H:%M")

            with formatter.indent():
                with file.open(mode="r", encoding="utf-8") as fp:
                    whole_plan = json.load(fp)
                fiammetta_targets = set()
                for plan in whole_plan["plans"]:
                    if (fiammetta := plan.get("Fiammetta")) is not None:
                        if fiammetta["enable"]:
                            fiammetta_targets.add(fiammetta["target"])

                    if not any(
                        start < update_time_str < end for start, end in plan["period"]
                    ):
                        continue
                    for (
                        skland_entry,
                        plan_entry,
                        facility_display_name,
                    ) in FACILITY_KEYS:
                        expected = [
                            set(room["operators"]) for room in plan["rooms"][plan_entry]
                        ]
                        actual = [
                            set(
                                character_info.operator_mapping[operator["charId"]]
                                for operator in room["chars"]
                            )
                            for room in iter_operator_from_skland_facility(
                                data, skland_entry
                            )
                        ]

                        for e, a in zip(*align_group(expected, actual)):
                            formatter.write(facility_display_name, ":")

                            missing = e - a
                            present = e & a
                            unexpected = a - e

                            for name in missing:
                                formatter.write_red_bold(f"-{name}", prefix=" ")
                            for name in present:
                                formatter.write_style(
                                    name,
                                    prefix=" ",
                                    bold=True,
                                )
                            for name in unexpected:
                                formatter.write_green_bold(
                                    f"+{name}",
                                    prefix=" ",
                                )
                            formatter.write("\n")

                if fiammetta_targets:
                    fiammetta_targets.add("菲亚梅塔")
                    for entry, _, __ in FACILITY_KEYS:
                        for room in iter_operator_from_skland_facility(data, entry):
                            for operator in room["chars"]:
                                name = character_info.operator_mapping[
                                    operator["charId"]
                                ]
                                if name not in fiammetta_targets:
                                    continue
                                fiammetta_targets.remove(name)
                                stamina = operator["ap"] / STAMINA_DIVIDOR
                                formatter.write_yellow_bold(name, suffix=": ")
                                if stamina <= STAMINA_REDLINE:
                                    formatter.write_red_bold(f"{stamina:.2f}")
                                else:
                                    formatter.write_green_bold(f"{stamina:.2f}")
                                if name == "菲亚梅塔":
                                    recovery_seconds = int(
                                        (FULL_STAMINA - stamina)
                                        / FIAMMETTA_RECOVER_PER_HOUR
                                        * 3600
                                    )
                                    formatter.write(
                                        f" (预计{display_timestamp(update_time + recovery_seconds)}回满)"
                                    )
                                formatter.write("\n")
                    if fiammetta_targets:
                        formatter.write_yellow_bold(
                            "没有找到的菲亚梅塔相关干员", suffix=":"
                        )
                        for name in fiammetta_targets:
                            formatter.write_red_bold(name, prefix=" ")
                        formatter.write("\n")
