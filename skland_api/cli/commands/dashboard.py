import asyncio
import importlib
import inspect
import itertools
from dataclasses import dataclass
from typing import Callable

import rich_click as click
from loguru import logger

from skland_api import AuthInfo, CharacterInfo, CharacterInfoLoader, SklandApiException

from .common import GlobalOptions, async_command


@dataclass(frozen=True, kw_only=True, slots=True)
class LoadedModule:
    name: str
    entry: Callable
    config: dict
    is_async: bool


@click.command(name="dashboard")
@click.option(
    "--modules",
    "modules_str",
    metavar="module1,module2,...",
    help="comma-separated module names to run",
)
@click.pass_context
@async_command
async def dashboard(
    ctx: click.Context,
    modules_str: str | None = None,
) -> None:
    global_options: GlobalOptions = ctx.obj

    if modules_str is not None:
        modules = modules_str.split(",")
    elif (config_modules := global_options.config.get("modules")) is not None:
        modules = config_modules
    else:
        # default modules
        modules = [
            "title",
            "checkin",
            "online",
            "stamina",
            "affair",
            "mission",
            "recruit",
            "base",
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
                logger.exception(
                    f"Module {module.name!r} execution failed for {character_info.name!r}"
                )
