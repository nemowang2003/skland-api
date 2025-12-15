import asyncio
import importlib
import itertools
import json
from functools import wraps
from pathlib import Path

import click

from skland_api import CharacterInfoLoader, SklandAuthInfo

APPNAME = "skland-api"


class Option(click.Option):
    def get_help_record(self, ctx: click.Context) -> tuple[str, str] | None:
        pass


def ensure_ctx_obj(ctx: click.Context) -> dict:
    if ctx.obj is None:
        ctx.obj = {}
    return ctx.obj


def create_auth_file(file: Path) -> None:
    while True:
        try:
            click.echo(
                "Add auth info for your first account!"
                "WARNING: All fields will be stored in PLAIN TEXT in:"
                f"  {file.absolute()}"
                "Anyone with access to this file can read them."
                ""
                "You must provide at least ONE of:"
                "  - phone (11 digits) AND password"
                "  - token (len=24)"
                "  - cred  (len=32)",
                err=True,
            )

            phone = click.prompt("Phone Number [Recommended]", default="")
            password = click.prompt("Password [Recommended]", default="")
            token = click.prompt("Token", default="")
            cred = click.prompt("Cred", default="")

            auth_info = SklandAuthInfo(
                phone=phone or None,
                password=password or None,
                token=token or None,
                cred=cred or None,
            )

            name = click.prompt("Name for this account")

            with file.open("w", encoding="utf-8") as fp:
                json.dump(
                    {name: auth_info.to_dict()},
                    fp,
                    ensure_ascii=True,
                    indent=2,
                )

            click.echo(f"Auth file created at: {file}", err=True)

        except ValueError as e:
            click.echo(f"Invalid information: {e}", err=True)
        except (EOFError, KeyboardInterrupt):
            click.echo("", err=True)
            raise click.Abort()


def create_config_file(file: Path):
    from .modules import default_modules

    with file.open("w", encoding="utf-8") as fp:
        json.dump(
            {"name": [], "modules": default_modules, "module-config": {}},
            fp,
            ensure_ascii=True,
            indent=2,
        )
    click.echo(f"Config file created at: {file}", err=True)


def prepare_config_dir(
    ctx: click.Context,
    parameter: click.Parameter,
    value: Path | None,
):
    if value is None:
        import platformdirs

        value = platformdirs.user_config_path(APPNAME)
    value.mkdir(parents=True, exist_ok=True)
    return value.expanduser()


def prepare_cache_dir(
    ctx: click.Context,
    parameter: click.Parameter,
    value: Path | None,
):
    if value is None:
        import platformdirs

        value = platformdirs.user_cache_path(APPNAME)
    value.mkdir(parents=True, exist_ok=True)
    return value.expanduser()


def prepare_auth_file(
    ctx: click.Context,
    parameter: click.Parameter,
    value: Path | None,
):
    obj = ensure_ctx_obj(ctx)
    if value is None:
        value = ctx.params["config_dir"] / "auth.json"
        if not value.exists() and not ctx.resilient_parsing:
            create_auth_file(value.expanduser())
    value = value.expanduser()
    with value.open(mode="r", encoding="utf-8") as fp:
        obj["auth"] = json.load(fp)
    return value


def prepare_config_file(
    ctx: click.Context,
    parameter: click.Parameter,
    value: Path | None,
):
    obj = ensure_ctx_obj(ctx)
    if value is None:
        value = ctx.params["config_dir"] / "config.json"
        if not value.exists():
            create_config_file(value)
    value = value.expanduser()
    with value.open(mode="r", encoding="utf-8") as fp:
        obj["config"] = json.load(fp)
    return value


def prepare_log_file(
    ctx: click.Context,
    parameter: click.Parameter,
    value: Path | None,
):
    if value is None:
        value = ctx.params["cache_dir"] / f"{APPNAME}.log"
    return value.expanduser()


def prepare_names(
    ctx: click.Context,
    parameter: click.Parameter,
    value: str | None,
):
    obj = ensure_ctx_obj(ctx)
    if value is not None:
        obj["names"] = value.split(",")
    return value


def prepare_modules(
    ctx: click.Context,
    parameter: click.Parameter,
    value: str | None,
):
    obj = ensure_ctx_obj(ctx)
    if value is not None:
        obj["modules"] = value.split(",")
    return value


def async_command(func):
    if not asyncio.iscoroutinefunction(func):
        raise ValueError(f"{func!r} is not async")

    @wraps(func)
    def inner(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return inner


@click.command()
@click.option("--names", metavar="name1,name2,...", callback=prepare_names, expose_value=False)
@click.option(
    "--modules",
    metavar="module1,module2,...",
    callback=prepare_modules,
    expose_value=False,
)
@click.option(
    "--config-dir",
    type=Path,
    metavar="<CONFIG_DIR>",
    envvar="SKLAND_API_CONFIG_DIR",
    show_envvar=True,
    callback=prepare_config_dir,
)
@click.option(
    "--cache-dir",
    type=Path,
    metavar="<CACHE_DIR>",
    envvar="SKLAND_API_CACHE_DIR",
    show_envvar=True,
    callback=prepare_cache_dir,
)
@click.option(
    "--auth-file",
    type=Path,
    metavar="<AUTH_FILE>",
    envvar="SKLAND_API_AUTH_FILE",
    show_envvar=True,
    callback=prepare_auth_file,
)
@click.option(
    "--config-file",
    type=Path,
    metavar="<CONFIG_FILE>",
    envvar="SKLAND_API_CONFIG_FILE",
    show_envvar=True,
    callback=prepare_config_file,
)
@click.option(
    "--log-file",
    type=Path,
    metavar="<LOG_FILE>",
    envvar="SKLAND_API_LOG_FILE",
    show_envvar=True,
    callback=prepare_log_file,
)
@click.pass_context
@async_command
async def main(
    ctx: click.Context,
    auth_file: Path,
    cache_dir: Path,
    log_file: Path,
    **_,
) -> None:
    from loguru import logger

    logger.add(log_file)

    obj = ensure_ctx_obj(ctx)
    auth = obj["auth"]
    config = obj["config"]
    if (names := obj.get("names")) is None:
        names = config.get("names") or list(auth.keys())
    if (modules := obj.get("modules")) is None:
        if (modules := config.get("modules")) is None:
            from .modules import default_modules

            modules = default_modules

    loaded_modules = []  # [(entry, config, is_async)]
    for module_name in modules:
        try:
            entry = importlib.import_module(f".modules.{module_name}", __package__).main
            is_async = asyncio.iscoroutinefunction(entry)
            loaded_modules.append((entry, config["module-config"].get(module_name), is_async))
        except ImportError:
            logger.exception(f"{module_name!r} is not a valid module")

    async def fetch_character_info(name: str) -> list:
        if (info := auth.get(name)) is None:
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
                result.dump(cache_dir)
                char_infos.append(result)

        return char_infos

    all_character_info = await asyncio.gather(*[fetch_character_info(name) for name in names])

    with auth_file.open(mode="w", encoding="utf-8") as fp:
        json.dump(auth, fp, ensure_ascii=False, indent=2)

    for character_info in itertools.chain.from_iterable(all_character_info):
        for entry, module_config, is_async in loaded_modules:
            if is_async:
                await entry(character_info, module_config)
            else:
                entry(character_info, module_config)
        print()
