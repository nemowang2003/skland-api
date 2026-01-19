import asyncio
import functools
import importlib
import json
import typing
from collections.abc import Coroutine
from dataclasses import dataclass
from functools import cached_property
from typing import Callable

import rich_click as click
from loguru import logger

from skland_api.api import SklandApiException
from skland_api.cli.core import GlobalOption, console, skland_command
from skland_api.models import AuthInfo, CharacterInfo, CharacterInfoLoader

from .formatter import render


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
        self, global_option: GlobalOption, names_str: str | None, modules_str: str | None
    ) -> None:
        self.global_option = global_option
        self.names_str = names_str
        self.modules_str = modules_str

        self.all_module_task = []
        self.async_tasks = []
        self.coroutines = []

    @cached_property
    def names(self) -> list[str]:
        if self.names_str is not None:
            names = self.names_str.split(",")
            unique_names = list(dict.fromkeys(names))
            if names != unique_names:
                logger.warning("Duplicate names found, duplicates will be ignored.")
            return unique_names
        return list(self.global_option.auth.keys())

    @cached_property
    def modules(self) -> list[str]:
        if self.modules_str is not None:
            modules = self.modules_str.split(",")
            unique_modules = list(dict.fromkeys(modules))
            if modules != unique_modules:
                logger.warning("Duplicate modules found, duplicates will be ignored.")
            return unique_modules
        return self.DEFAULT_MODULES

    @cached_property
    def module_registry(self) -> dict[str, LoadedModule]:
        registry = {}

        for module_name in self.modules:
            try:
                entry = importlib.import_module(
                    f".formatter.{module_name}", __package__
                ).module_entry
                registry[module_name] = LoadedModule(
                    entry=entry,
                    is_async=asyncio.iscoroutinefunction(entry),
                )
            except ImportError:
                logger.error(f"{module_name!r} is not a valid module")

        return registry

    async def fetch_character_info(self, name: str) -> list[CharacterInfo]:
        if (info := self.global_option.auth.get(name)) is None:
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
                result.dump_to(self.global_option.cache_dir)
                char_infos.append(result)

        return char_infos

    def build_all_module_tasks(self, all_character_info: list[list[CharacterInfo]]) -> None:
        for name, character_infos in zip(self.names, all_character_info):
            module_tasks: list[ModuleTask] = []
            for character_info in character_infos:
                for module_name in self.modules:
                    module = self.module_registry[module_name]
                    module_task = ModuleTask(
                        user_name=name,
                        module_name=module_name,
                        entry=functools.partial(
                            module.entry,
                            character_info,
                            self.global_option.config["module-config"].get(module_name),
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
            task = typing.cast(ModuleTask, task)
            task.entry = functools.partial(return_result, result)


@skland_command(name="dashboard")
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
async def dashboard(
    global_option: GlobalOption, names_str: str | None = None, modules_str: str | None = None
) -> None:
    launcher = DashBoardLauncher(global_option, names_str, modules_str)

    all_character_info = await asyncio.gather(
        *[launcher.fetch_character_info(name) for name in launcher.names]
    )
    with global_option.auth_file.open("w") as fp:
        json.dump(global_option.auth, fp, ensure_ascii=True, indent=2)
    launcher.build_all_module_tasks(all_character_info)
    await launcher.run_async_tasks_and_patch_module_tasks()

    for tasks in launcher.all_module_task:
        for task in tasks:
            result = task.entry()
            if isinstance(result, BaseException):
                logger.error(
                    f"Module {task.module_name!r} for user {task.user_name!r} failed: {result}"
                )
            else:
                console.print(render(result))


def return_result(result):
    return result


__all__ = [
    "dashboard",
]
