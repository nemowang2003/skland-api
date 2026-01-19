try:
    import rich_click as click
except ImportError:
    import sys

    print(
        "错误: 未找到运行命令行界面 (CLI) 所需的必要依赖。\n"
        "请参考项目根目录下的 README.md 进行安装。",
        file=sys.stderr,
    )
    sys.exit(1)


from .commands.dashboard import dashboard
from .core import skland_group

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"


@skland_group(
    help="森空岛 (Skland) API 命令行工具",
    default_command="dashboard",
)
def main(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(dashboard)


main.add_command(dashboard)

__all__ = [
    "main",
]
