import asyncio
import importlib
import itertools
import json

import typer
from loguru import logger

from skland_api import CharacterInfoLoader, SklandAuthInfo

from .common import GlobalOptions, async_command

app = typer.Typer()


@app.command()
@async_command
async def show(
    ctx: typer.Context,
) -> None:
    global_options: GlobalOptions = ctx.obj

    loaded_modules = []  # [(entry, config, is_async)]
    for module_name in global_options.modules:
        try:
            entry = importlib.import_module(f"skland_api.cli.modules.{module_name}").main
            is_async = asyncio.iscoroutinefunction(entry)
            loaded_modules.append(
                (entry, global_options.config["module-config"].get(module_name), is_async)
            )
        except ImportError:
            logger.exception(f"{module_name!r} is not a valid module")

    async def fetch_character_info(name: str) -> list:
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
                result.dump(global_options.cache_dir)
                char_infos.append(result)

        return char_infos

    all_character_info = await asyncio.gather(
        *[fetch_character_info(name) for name in global_options.names]
    )

    with global_options.auth_file.open(mode="w", encoding="utf-8") as fp:
        json.dump(global_options.auth, fp, ensure_ascii=False, indent=2)

    for character_info in itertools.chain.from_iterable(all_character_info):
        for entry, module_config, is_async in loaded_modules:
            if is_async:
                await entry(character_info, module_config)
            else:
                entry(character_info, module_config)
        print()
