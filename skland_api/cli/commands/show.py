import asyncio
import importlib
import inspect
import itertools
from dataclasses import dataclass
from typing import Callable

import rich_click as click
from loguru import logger

from skland_api import CharacterInfo, CharacterInfoLoader, SklandAuthInfo

from .common import GlobalOptions, async_command


@dataclass(frozen=True, kw_only=True, slots=True)
class LoadedModule:
    name: str
    entry: Callable
    config: dict
    is_async: bool


@click.command()
@click.pass_context
@async_command
async def show(
    ctx: click.Context,
) -> None:
    global_options: GlobalOptions = ctx.obj

    loaded_modules: list[LoadedModule] = []
    for module_name in global_options.modules:
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
            logger.exception(f"{module_name!r} is not a valid module")

    async def fetch_character_info(name: str) -> list[CharacterInfo]:
        if (info := global_options.auth.get(name)) is None:
            logger.error(f"name {name!r} not in auth file")
            return []
        try:
            auth_info = SklandAuthInfo(**info)
            api = await auth_info.full_auth()
            info.update(auth_info.to_dict())
        except Exception:
            logger.exception(f"User {name} login failed")
            return []
        try:
            characters = await api.binding_list()
        except Exception:
            logger.exception(f"User {name} fetch binding list failed")
            return []

        loader_tasks = [
            CharacterInfoLoader(name, api, character).full_load()
            for character in characters
            if character["gameName"] == "明日方舟"
        ]

        results = await asyncio.gather(*loader_tasks, return_exceptions=True)

        char_infos = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"Failed to load character info: {result}")
            else:
                result.dump_to(global_options.cache_dir)
                char_infos.append(result)

        return char_infos

    all_character_info = await asyncio.gather(
        *[fetch_character_info(name) for name in global_options.names]
    )

    global_options.update_auth_file()

    for character_info in itertools.chain.from_iterable(all_character_info):
        for module in loaded_modules:
            try:
                if module.is_async:
                    await module.entry(character_info, module.config)
                else:
                    module.entry(character_info, module.config)
            except Exception:
                logger.exception(f"Module {module.name!r} execution failed")
                raise
