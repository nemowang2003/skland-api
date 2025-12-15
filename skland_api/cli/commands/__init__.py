from pathlib import Path

import platformdirs
import rich_click as click
from loguru import logger

from .common import APPNAME, GlobalOptions
from .show import show

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"


@click.group(invoke_without_command=True, help="Skland API CLI Tool")
@click.option(
    "--names",
    "names_str",
    is_eager=True,
    metavar="name1,name2,...",
    help="comma-separated account names to query",
)
@click.option(
    "--modules",
    "modules_str",
    is_eager=True,
    metavar="module1,module2,...",
    help="comma-separated module names to run",
)
@click.option(
    "--config-dir",
    is_eager=True,
    envvar="SKLAND_API_CONFIG_DIR",
    show_envvar=True,
    type=click.Path(path_type=Path),
    default=lambda: platformdirs.user_config_path(APPNAME, ensure_exists=True),
    help="configuration directory",
)
@click.option(
    "--cache-dir",
    is_eager=True,
    envvar="SKLAND_API_CACHE_DIR",
    show_envvar=True,
    type=click.Path(path_type=Path),
    default=lambda: platformdirs.user_cache_path(APPNAME, ensure_exists=True),
    help="cache directory",
)
@click.option(
    "--auth-file",
    is_eager=True,
    envvar="SKLAND_API_AUTH_FILE",
    show_envvar=True,
    type=click.Path(path_type=Path),
    help="authentication file path",
)
@click.option(
    "--config-file",
    is_eager=True,
    envvar="SKLAND_API_CONFIG_FILE",
    show_envvar=True,
    type=click.Path(path_type=Path),
    help="configuration file path",
)
@click.option(
    "--log-file",
    is_eager=True,
    envvar="SKLAND_API_LOG_FILE",
    show_envvar=True,
    type=click.Path(path_type=Path),
    help="log file path",
)
@click.pass_context
def main(
    ctx: click.Context,
    names_str: str | None,
    modules_str: str | None,
    config_dir: Path,
    cache_dir: Path,
    auth_file: Path | None,
    config_file: Path | None,
    log_file: Path | None,
):
    global_options = GlobalOptions.from_command_line_options(
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
        ctx.invoke(show)


main.add_command(show)
