from pathlib import Path

try:
    import platformdirs
    import rich_click as click
except ImportError:
    import sys

    print(
        "错误: 运行命令行界面 (CLI) 需要安装额外的依赖。\n"
        "请运行以下命令进行安装: pip install 'skland-api[cli]'",
        file=sys.stderr,
    )
    sys.exit(1)

from loguru import logger

from .common import APPNAME, GlobalOptions
from .dashboard import dashboard

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"


@click.group(help="森空岛 (Skland) API 命令行工具")
@click.option(
    "--config-dir",
    envvar="SKLAND_API_CONFIG_DIR",
    show_envvar=True,
    type=click.Path(path_type=Path),
    default=lambda: platformdirs.user_config_path(APPNAME, ensure_exists=True),
    help="配置文件存放目录",
)
@click.option(
    "--cache-dir",
    envvar="SKLAND_API_CACHE_DIR",
    show_envvar=True,
    type=click.Path(path_type=Path),
    default=lambda: platformdirs.user_cache_path(APPNAME, ensure_exists=True),
    help="缓存文件存放目录",
)
@click.option(
    "--auth-file",
    envvar="SKLAND_API_AUTH_FILE",
    show_envvar=True,
    type=click.Path(path_type=Path),
    help="认证信息文件 (auth.json) 的具体路径",
)
@click.option(
    "--config-file",
    envvar="SKLAND_API_CONFIG_FILE",
    show_envvar=True,
    type=click.Path(path_type=Path),
    help="配置文件 (config.json) 的具体路径",
)
@click.option(
    "--log-file",
    envvar="SKLAND_API_LOG_FILE",
    show_envvar=True,
    type=click.Path(path_type=Path),
    help="日志文件的输出路径",
)
@click.pass_context
def main(
    ctx: click.Context,
    config_dir: Path,
    cache_dir: Path,
    auth_file: Path | None,
    config_file: Path | None,
    log_file: Path | None,
):
    global_options = GlobalOptions.from_command_line_options(
        config_dir=config_dir,
        auth_file=auth_file,
        config_file=config_file,
        cache_dir=cache_dir,
        log_file=log_file,
    )

    logger.add(global_options.log_file)

    ctx.obj = global_options


main.add_command(dashboard)

__all__ = [
    "main",
]
