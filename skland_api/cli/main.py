import importlib
import json
from pathlib import Path

import click

from skland_api import CharacterInfo, SklandAuthInfo

from .utils.logger import LogFormatter

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
            click.echo("Add auth info for your first account!", err=True)
            click.echo("WARNING: All fields will be stored in PLAIN TEXT in:", err=True)
            click.echo(f"  {file.absolute()}", err=True)
            click.echo("Anyone with access to this file can read them.", err=True)
            click.echo("", err=True)
            click.echo("You must provide at least ONE of:", err=True)
            click.echo("  - phone (11 digits) AND password", err=True)
            click.echo("  - token (len=24)", err=True)
            click.echo("  - cred  (len=32)", err=True)

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
                    {name: auth_info.as_dict()},
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
def main(
    ctx: click.Context,
    auth_file: Path,
    cache_dir: Path,
    log_file: Path,
    **_,
) -> None:
    import logging

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(LogFormatter(color=True))
    root_logger.addHandler(stderr_handler)

    file_handler = logging.FileHandler(filename=log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(LogFormatter(color=False))
    root_logger.addHandler(file_handler)

    logger = logging.getLogger(__name__)

    obj = ensure_ctx_obj(ctx)
    auth = obj["auth"]
    config = obj["config"]
    if (names := obj.get("names")) is None:
        names = config.get("names") or list(auth.keys())
    if (modules := obj.get("modules")) is None:
        if (modules := config.get("modules")) is None:
            from .modules import default_modules

            modules = default_modules

    for name in names:
        if (info := auth.get(name)) is None:
            logger.error(f"name {name!r} not in auth file")
            continue
        auth_info = SklandAuthInfo(**info)
        api = auth_info.full_auth()
        info.update(auth_info.as_dict())

        for character in api.binding_list():
            character_info = CharacterInfo(name, api, character)
            character_info.dump(cache_dir)

            for module_name in modules:
                module = importlib.import_module(f".modules.{module_name}", __package__)
                if module is not None:
                    module.main(
                        character_info,
                        config["module-config"].get(module_name),
                    )
                else:
                    logger.error(f"{module_name!r} is not a valid module")
            print()
    with auth_file.open(mode="w", encoding="utf-8") as fp:
        json.dump(auth, fp, ensure_ascii=False, indent=2)
