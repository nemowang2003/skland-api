import importlib.util

try:
    for module in ["platformdirs", "rich", "tomlkit"]:
        if importlib.util.find_spec(module) is None:
            raise ImportError(name=module)
    import rich_click as click
except ImportError as e:
    import sys

    print(
        f"错误: 未找到运行命令行界面 (CLI) 所需的必要依赖: {e.name!r}。\n"
        "这不一定是全部缺少的依赖，请参考项目根目录下的 README.md 进行安装。",
        file=sys.stderr,
    )
    sys.exit(1)

import importlib.metadata

from loguru import logger

from .commands.auth import auth
from .commands.dashboard import dashboard
from .core import APPNAME, skland_group

logger.remove()

try:
    __version__ = importlib.metadata.version(APPNAME)
except Exception:
    __version__ = "unknown"

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"


@skland_group(
    help="森空岛 (Skland) API 命令行工具",
    default_command="dashboard",
)
@click.version_option(version=__version__, prog_name=APPNAME)
def main(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(dashboard)


main.add_command(auth)
main.add_command(dashboard)

__all__ = [
    "main",
]
