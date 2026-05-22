import asyncio
import functools
import importlib
from collections.abc import Coroutine
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Callable

import rich_click as click
from loguru import logger
from tomlkit.items import Table

from skland_api.api import SklandApiException
from skland_api.cli.core import (
    AuthFailure,
    GlobalOption,
    console,
    load_auth_info,
    save_auth_info,
    skland_command,
)
from skland_api.models import CharacterInfo, CharacterInfoLoader

from .formatter import render


class TomlField:
    def __init__(self, key: str | None, default_factory: Callable[[], Any]):
        self.key = key
        self.default_factory = default_factory

    def __set_name__(self, owner, name):
        if self.key is None:
            self.key = name

    def __get__(self, obj, objtype):
        return obj._table.get(self.key, self.default_factory())

    def __set__(self, obj, value):
        if value is None:
            obj._table.pop(self.key, None)
        else:
            obj._table[self.key] = value

    def __delete__(self, obj):
        obj._table.pop(self.key, None)


def toml_field(key: str | None = None, default_factory=lambda: None):
    return TomlField(key, default_factory)


class UserConfig:
    enabled: bool = toml_field(default_factory=lambda: True)
    extra_modules: list[str] | None = toml_field(key="extra-modules")
    all_modules: list[str] | None = toml_field(key="all-modules")

    def __init__(self, name: str, table: Table):
        self.name = name
        self._table = table

    @property
    def module_config(self) -> dict:
        return self._table.get("module", {})


@dataclass(frozen=True, kw_only=True, slots=True)
class LoadedModule:
    entry: Callable
    is_async: bool


@dataclass(kw_only=True, slots=True)
class ModuleTask:
    user_name: str
    module_name: str
    entry: Callable


class DashBoardLauncher:
    DEFAULT_MODULES = [
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
    all_module_task: list[list[ModuleTask]]
    async_tasks: list[ModuleTask]
    coroutines: list[Coroutine]

    def __init__(
        self, global_option: GlobalOption, users: list[str] | None, modules: list[str] | None
    ) -> None:
        self.global_option = global_option

        if users is not None:
            unique_users = list(dict.fromkeys(users))
            if users != unique_users:
                logger.warning("发现了重复的 users，已自动去重")
            users = unique_users
        self.users = users

        if modules is not None:
            unique_modules = list(dict.fromkeys(modules))
            if modules != unique_modules:
                logger.warning("发现了重复的 modules，已自动去重")
            modules = unique_modules
        self.modules = modules

        self.all_module_task = []
        self.async_tasks = []
        self.coroutines = []

    @cached_property
    def user_config(self) -> dict[str, UserConfig]:
        user_config = {}
        for user, config in self.global_option.config_content.items():
            if not isinstance(config, Table):
                logger.error(f"{user!r} 的配置格式不正确，未解析成功")
                continue
            user_config[user] = UserConfig(user, config)
        return user_config

    @cached_property
    def users_to_run(self) -> list[str]:
        if self.users is not None:
            return self.users
        return [config.name for config in self.user_config.values() if config.enabled]

    def get_user_config(self, user: str) -> UserConfig:
        config = self.user_config.get(user)
        if config is None:
            raise click.ClickException(f"用户 {user!r} 不存在于配置文件中")
        return config

    @cached_property
    def modules_to_load(self) -> set[str]:
        if self.modules is not None:
            return set(self.modules)
        modules = set()
        for user in self.users_to_run:
            config = self.get_user_config(user)
            all_modules = config.all_modules
            extra_modules = config.extra_modules
            if all_modules is not None:
                modules.update(all_modules)
                if extra_modules is not None:
                    logger.warning(
                        f"{user!r}同时配置了 all-modules 和 extra-modules。"
                        "extra-modules 的值将被忽略"
                    )
            else:
                modules.update(self.DEFAULT_MODULES)
            if extra_modules is not None:
                modules.update(extra_modules)
        return modules

    @cached_property
    def module_registry(self) -> dict[str, LoadedModule]:
        registry = {}

        for module_name in self.modules_to_load:
            try:
                entry = importlib.import_module(
                    f".formatter.{module_name}", __package__
                ).module_entry
                registry[module_name] = LoadedModule(
                    entry=entry,
                    is_async=asyncio.iscoroutinefunction(entry),
                )
            except ImportError:
                logger.error(f"无法导入 module {module_name!r}")

        return registry

    async def fetch_character_info(self, user: str) -> list[CharacterInfo]:
        try:
            auth_info = load_auth_info(self.global_option.auth_dir, user)
            api = await auth_info.full_auth()
            save_auth_info(self.global_option.auth_dir, user, auth_info)
        except AuthFailure as e:
            logger.error(f"{user!r} 认证信息无效: {e.format_message()}")
            return []
        except ValueError:
            logger.error(f"{user!r} 认证失败")
            return []
        try:
            characters = await api.binding_list()
        except SklandApiException as e:
            logger.error(f"{user!r} 获取绑定信息失败: {e}")
            return []

        loader_tasks = [
            CharacterInfoLoader(user, api, character).full_load()
            for character in characters
            if character["gameName"] == "明日方舟"
        ]

        results = await asyncio.gather(*loader_tasks, return_exceptions=True)

        char_infos: list[CharacterInfo] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"获取角色信息失败: {result}")
            else:
                result.dump_to(self.global_option.cache_dir)
                char_infos.append(result)

        return char_infos

    def build_all_module_tasks(self, all_character_info: list[list[CharacterInfo]]) -> None:
        for user, character_infos in zip(self.users_to_run, all_character_info):
            module_tasks: list[ModuleTask] = []
            for character_info in character_infos:
                config = self.get_user_config(user)
                modules_to_run = config.all_modules or self.DEFAULT_MODULES + (
                    config.extra_modules or []
                )
                for module_name in modules_to_run:
                    module = self.module_registry.get(module_name)
                    if module is None:
                        logger.error(f"module {module_name!r} 未加载成功，已跳过")
                        continue
                    module_task = ModuleTask(
                        user_name=user,
                        module_name=module_name,
                        entry=functools.partial(
                            module.entry,
                            character_info,
                            self.user_config[user].module_config.get(module_name),
                        ),
                    )
                    module_tasks.append(module_task)
                    if module.is_async:
                        self.async_tasks.append(module_task)
                        self.coroutines.append(module_task.entry())

            self.all_module_task.append(module_tasks)

    async def run_async_tasks_and_patch_module_tasks(self) -> None:
        for task, result in zip(
            self.async_tasks,
            await asyncio.gather(*self.coroutines, return_exceptions=True),
        ):
            task.entry = functools.partial(return_result, result)


@skland_command(name="dashboard", help="数据看板")
@click.option(
    "--users",
    metavar="user1,user2,...",
    help="要查询的账号名称列表，使用逗号分割",
)
@click.option(
    "--modules",
    metavar="module1,module2,...",
    help="要运行的功能模块列表，使用逗号分隔",
)
async def dashboard(global_option: GlobalOption, users: str | None, modules: str | None):
    launcher = DashBoardLauncher(
        global_option,
        users.split(",") if users is not None else None,
        modules.split(",") if modules is not None else None,
    )

    if not launcher.users_to_run:
        raise click.ClickException("没有可以运行的账号，请使用 `skland auth add` 添加账号")

    all_character_info = await asyncio.gather(
        *[launcher.fetch_character_info(name) for name in launcher.users_to_run]
    )
    global_option.writeback()
    launcher.build_all_module_tasks(all_character_info)
    await launcher.run_async_tasks_and_patch_module_tasks()

    for tasks in launcher.all_module_task:
        for task in tasks:
            result = task.entry()
            if isinstance(result, BaseException):
                logger.error(
                    f"{task.user_name!r} 的 module {task.module_name!r} 执行失败: {result}"
                )
            else:
                console.print(render(result))


def return_result(result):
    return result


__all__ = [
    "dashboard",
]
