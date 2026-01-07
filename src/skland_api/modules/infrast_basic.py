from dataclasses import dataclass

from skland_api.models import Capacity, CharacterInfo, Duration, Progress, TimeStamp

TOTAL_TRAIN_POINT = [30000, 60000, 90000]
# 基础速度为 8h 完成专精一级, 即 30000 点数
BASIC_TRAIN_PER_SECOND = 30000 / 8 / 3600


@dataclass(frozen=True, kw_only=True, slots=True)
class Mastery:
    trainee_name: str
    skill_id: int
    skill_mastery_level: int
    trainer_name: str | None
    speed: float
    progress: Progress
    remain_seconds: Duration


def get_mastery(character_info: CharacterInfo) -> Mastery | None:
    mastery_data = character_info.player_info["building"]["training"]
    update_time = character_info.player_info["status"]["storeTs"]
    sec_since_update = Duration.to_now(TimeStamp(update_time))

    trainee = mastery_data["trainee"]
    if trainee is None or trainee["targetSkill"] == -1:
        return None

    trainee_name = character_info.operator_name_mapping_with_fix[trainee["charId"]]
    skill_id = trainee["targetSkill"]
    skill_mastery_level = character_info.operators[trainee["charId"]].mastery_levels[skill_id]

    trainer = mastery_data["trainer"]
    trainer_name = trainer or character_info.operator_name_mapping[trainer["charId"]]

    speed = mastery_data["speed"]
    total = TOTAL_TRAIN_POINT[skill_mastery_level]
    # 计算当前专精进度
    current = (
        total - mastery_data["remainPoint"] + BASIC_TRAIN_PER_SECOND * speed * sec_since_update
    )
    progress = Progress(min(int(current), total), total)
    # 专精的 remainSecs 数据按照请求时间计算（与无人机的 remainSecs 不同）
    remain_seconds = Duration(mastery_data["remainSecs"])

    return Mastery(
        trainee_name=trainee_name,
        skill_id=skill_id,
        skill_mastery_level=skill_mastery_level,
        trainer_name=trainer_name,
        speed=speed,
        progress=progress,
        remain_seconds=remain_seconds,
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class InfrastOverview:
    """
    drones: 预计无人机数量
    dronse_full_in: 预计无人机补满时间
    exhausted_operators: 疲劳干员列表
    mastery: 专精状态
    """

    drones: Capacity
    drones_full_in: Duration
    exhausted_operators: list[str]
    mastery: Mastery | None


def main(character_info: CharacterInfo, config: dict | None) -> InfrastOverview:
    data = character_info.player_info["building"]
    update_time = character_info.player_info["status"]["storeTs"]

    drones_data = data["labor"]
    current = drones_data["value"]
    total = drones_data["maxValue"]
    remain_seconds = drones_data["remainSecs"]

    if remain_seconds > 0:
        # 无人机的 remainSecs 数据按照更新时间计算（与专精的 remainSecs 不同）
        sec_since_update = Duration.to_now(update_time)
        approximate_recover_speed = (total - current) / remain_seconds
        current = min(
            current + int(sec_since_update * approximate_recover_speed),
            total,
        )
        remain_seconds = remain_seconds - sec_since_update

    drones = Capacity(current, total)
    drones_full_in = Duration(remain_seconds)
    exhausted_operators = [
        character_info.operator_name_mapping[char["charId"]] for char in data["tiredChars"]
    ]
    mastery = get_mastery(character_info)
    return InfrastOverview(
        drones=drones,
        drones_full_in=drones_full_in,
        exhausted_operators=exhausted_operators,
        mastery=mastery,
    )
