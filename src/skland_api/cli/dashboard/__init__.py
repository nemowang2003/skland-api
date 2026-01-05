import asyncio
import importlib
import inspect
import itertools
import typing
from dataclasses import dataclass
from typing import Callable

import rich_click as click
from loguru import logger

from skland_api.api import SklandApiException
from skland_api.models import AuthInfo, CharacterInfo, CharacterInfoLoader

from ..common import GlobalOptions, async_command


@dataclass(frozen=True, kw_only=True, slots=True)
class LoadedModule:
    name: str
    entry: Callable
    config: dict
    is_async: bool


@click.command(name="dashboard")
@click.option(
    "--names",
    "names_str",
    metavar="name1,name2,...",
    help="要查询的账号名称列表，使用逗号分割",
)
@click.option(
    "--modules",
    "modules_str",
    metavar="module1,module2,...",
    help="要运行的功能模块列表，使用逗号分隔",
)
@click.pass_context
@async_command
async def dashboard(
    ctx: click.Context,
    names_str: str | None = None,
    modules_str: str | None = None,
) -> None:
    """展示明日方舟游戏数据看板。

    该命令会遍历配置中的所有账号，获取其绑定的角色信息，并依次执行指定的功能模块。支持的模块包括:

    默认模块:

    - profile       : 玩家个人信息
    - update        : 数据更新时间
    - checkin       : 每日签到
    - online        : 上次在线时间
    - sanity        : 当前理智
    - routine       : 剿灭/保全派驻进度
    - mission       : 每日/每周任务进度
    - recruit       : 公开招募进度
    - infrast_basic : 基建概览

    如果没有指定 --modules, 将按上述顺序运行所有默认模块。

    其它模块:

    - infrast_assignment : 基建排班表审计与菲亚梅塔监控, 需要提供 MAA 换班表
    """
    global_options = typing.cast(GlobalOptions, ctx.obj)

    if names_str is not None:
        names = names_str.split(",")
    else:
        names = list(global_options.auth.keys())

    unique_names = list(dict.fromkeys(names))
    if names != unique_names:
        logger.warning("Duplicate names found, duplicates will be ignored.")
        names = unique_names

    if modules_str is not None:
        modules = modules_str.split(",")
    else:
        # default modules
        modules = [
            "profile",
            "update",
            "checkin",
            "online",
            "sanity",
            "routine",
            "mission",
            "recruit",
            "infrast_basic",
        ]

    unique_modules = list(dict.fromkeys(modules))
    if modules != unique_modules:
        logger.warning("Duplicate modules found, duplicates will be ignored.")
        modules = unique_modules

    loaded_modules: list[LoadedModule] = []
    for module_name in modules:
        try:
            entry = importlib.import_module(f"skland_api.modules.{module_name}").main
            loaded_modules.append(
                LoadedModule(
                    name=module_name,
                    entry=entry,
                    config=global_options.config["module-config"].get(module_name),
                    is_async=inspect.iscoroutinefunction(entry),
                )
            )
        except ImportError:
            logger.error(f"{module_name!r} is not a valid module")

    async def fetch_character_info(name: str) -> list[CharacterInfo]:
        if (info := global_options.auth.get(name)) is None:
            logger.error(f"name {name!r} not in auth file")
            return []
        try:
            auth_info = AuthInfo(**info)
            api = await auth_info.full_auth()
            info.update(auth_info.to_dict())
        except ValueError:
            logger.error(f"User {name} login failed")
            return []
        try:
            characters = await api.binding_list()
        except SklandApiException as e:
            logger.error(f"User {name} fetch binding list failed: {e}")
            return []

        loader_tasks = [
            CharacterInfoLoader(name, api, character).full_load()
            for character in characters
            if character["gameName"] == "明日方舟"
        ]

        results = await asyncio.gather(*loader_tasks, return_exceptions=True)

        char_infos: list[CharacterInfo] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"Failed to load character info: {result}")
            else:
                result.dump_to(global_options.cache_dir)
                char_infos.append(result)

        return char_infos

    all_character_info = await asyncio.gather(*[fetch_character_info(name) for name in names])

    global_options.update_auth_file()

    for character_info in itertools.chain.from_iterable(all_character_info):
        for module in loaded_modules:
            try:
                if module.is_async:
                    await module.entry(character_info, module.config)
                else:
                    module.entry(character_info, module.config)
            except Exception:
                logger.exception(
                    f"Module {module.name!r} execution failed for {character_info.name!r}"
                )


__all__ = [
    "dashboard",
]
