from pathlib import Path
from typing import Annotated

import platformdirs
import typer
from loguru import logger

from .common import APPNAME, GlobalOptions
from .show import app as show_app
from .show import show

app = typer.Typer(rich_markup_mode="rich", help="Skland API CLI Tool")
app.add_typer(show_app)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            envvar="SKLAND_API_CONFIG_DIR",
            default_factory=lambda: platformdirs.user_config_path(APPNAME, ensure_exists=True),
            help="configuration directory",
        ),
    ],
    cache_dir: Annotated[
        Path,
        typer.Option(
            "--cache-dir",
            envvar="SKLAND_API_CACHE_DIR",
            default_factory=lambda: platformdirs.user_cache_path(APPNAME, ensure_exists=True),
            help="cache directory",
        ),
    ],
    names_str: Annotated[
        str | None,
        typer.Option(
            "--names",
            metavar="name1,name2,...",
            help="comma-separated account names to query",
        ),
    ] = None,
    modules_str: Annotated[
        str | None,
        typer.Option(
            "--modules",
            metavar="module1,module2,...",
            help="comma-separated module names to run",
        ),
    ] = None,
    auth_file: Annotated[
        Path | None,
        typer.Option(
            "--auth-file",
            envvar="SKLAND_API_AUTH_FILE",
            help="authentication file path",
        ),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config-file",
            envvar="SKLAND_API_CONFIG_FILE",
            help="configuration file path",
        ),
    ] = None,
    log_file: Annotated[
        Path | None,
        typer.Option(
            "--log-file",
            envvar="SKLAND_API_LOG_FILE",
            help="log file path",
        ),
    ] = None,
):
    global_options = GlobalOptions.construct_with_fallback(
        names=names_str.split(",") if names_str is not None else None,
        modules=modules_str.split(",") if modules_str is not None else None,
        config_dir=config_dir,
        auth_file=auth_file,
        config_file=config_file,
        cache_dir=cache_dir,
        log_file=log_file,
    )
    logger.add(global_options.log_file)
    ctx.obj = global_options

    if ctx.invoked_subcommand is None:
        show(ctx)
