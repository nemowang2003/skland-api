import asyncio
import functools
import inspect
import json
import typing
from collections.abc import Callable
from dataclasses import dataclass
from gettext import gettext as _
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Concatenate

import platformdirs
import rich_click as click
from click.core import ParameterSource
from rich.console import Console

APPNAME = "skland-api"
console = Console()


@dataclass(frozen=True, kw_only=True, slots=True)
class GlobalOption:
    auth_file: Path
    auth: dict
    config: dict
    cache_dir: Path
    log_file: Path


@dataclass(slots=True)
class GlobalOptionBuilder:
    click_options: ClassVar = [
        click.RichOption(
            ["--config-dir"],
            envvar="SKLAND_API_CONFIG_DIR",
            show_envvar=True,
            type=click.Path(path_type=Path),
            default=lambda: platformdirs.user_config_path(APPNAME, ensure_exists=True),
            help="配置文件存放目录",
        ),
        click.RichOption(
            ["--cache-dir"],
            envvar="SKLAND_API_CACHE_DIR",
            show_envvar=True,
            type=click.Path(path_type=Path),
            default=lambda: platformdirs.user_cache_path(APPNAME, ensure_exists=True),
            help="缓存文件存放目录",
        ),
        click.RichOption(
            ["--auth-file"],
            envvar="SKLAND_API_AUTH_FILE",
            show_envvar=True,
            type=click.Path(path_type=Path),
            help="认证信息文件 (auth.json) 的具体路径",
        ),
        click.RichOption(
            ["--config-file"],
            envvar="SKLAND_API_CONFIG_FILE",
            show_envvar=True,
            type=click.Path(path_type=Path),
            help="配置文件 (config.json) 的具体路径",
        ),
        click.RichOption(
            ["--log-file"],
            envvar="SKLAND_API_LOG_FILE",
            show_envvar=True,
            type=click.Path(path_type=Path),
            help="日志文件的输出路径",
        ),
    ]

    config_dir: Path | None = None
    auth_file: Path | None = None
    config_file: Path | None = None
    cache_dir: Path | None = None
    log_file: Path | None = None

    def set(self, k: str, v) -> None:
        setattr(self, k, v)

    def setdefault(self, k: str, v) -> None:
        if getattr(self, k) is None:
            setattr(self, k, v)

    def build(self) -> GlobalOption:
        if self.config_dir is None:
            raise RuntimeError("未设置 config_dir")
        config_dir = self.config_dir.expanduser().resolve()
        if not config_dir.is_dir():
            raise NotADirectoryError(config_dir)
        if self.cache_dir is None:
            raise ValueError("未设置 cache_dir")
        cache_dir = self.cache_dir.expanduser().resolve()
        if not cache_dir.is_dir():
            raise NotADirectoryError(cache_dir)

        if self.auth_file is not None:
            auth_file = self.auth_file.expanduser().resolve()
        else:
            auth_file = config_dir / "auth.json"
        if not auth_file.exists():
            raise NotImplementedError
        with auth_file.open(encoding="utf-8") as fp:
            auth = json.load(fp)

        if self.config_file is not None:
            config_file = self.config_file.expanduser().resolve()
        else:
            config_file = config_dir / "config.json"
        if not config_file.exists():
            raise NotImplementedError
        with config_file.open(encoding="utf-8") as fp:
            config = json.load(fp)

        if self.log_file is not None:
            log_file = self.log_file.expanduser().resolve()
        else:
            log_file = cache_dir / f"{APPNAME}.log"

        return GlobalOption(
            auth_file=auth_file,
            auth=auth,
            config=config,
            cache_dir=cache_dir,
            log_file=log_file,
        )


if TYPE_CHECKING:
    # 这实际上不对，但确实没法为 Mixin 类型标注它在所有情况下的 Base
    MixinBase = click.Command
else:
    MixinBase = object

# 接下来的类型标注其实并不完全正确，而且可能并没有什么实际用处，
# 但总之它们在 ty v0.0.12 下通过了检查。
type MixinInput[**P, R] = Callable[Concatenate[click.Context, P], R]
type CommandInput[**P, R] = Callable[Concatenate[GlobalOption, P], R]


class Mixin(MixinBase):
    def __init__(self, **kwargs):
        kwargs.setdefault("params", [])
        kwargs["params"].extend(GlobalOptionBuilder.click_options)
        callback = kwargs.get("callback")
        if callback is not None:
            kwargs["callback"] = self.wrap_callback(callback)
        super().__init__(**kwargs)

    @staticmethod
    def wrap_callback[**P, R](f: MixinInput[P, R]) -> Callable[P, R]:
        """
        将实际定义时的 def command(ctx: click.Context, option1, option2, ...)
        转化成 click 的标准格式
        def inner(**kwargs)
        然后将 kwargs 中的 global options 部分放进 ctx.obj 中
        剩余的就是 command 定义的各个 option
        先将 ctx 作为第一个参数，然后将 kwargs 原样转发给原本的 command
        """

        @functools.wraps(f)
        def inner(**kwargs) -> R:
            ctx = typing.cast(click.Context, click.get_current_context())
            builder = ctx.ensure_object(GlobalOptionBuilder)
            for option in GlobalOptionBuilder.click_options:
                name = option.name
                if name is None:
                    continue
                if ctx.get_parameter_source(name) == ParameterSource.COMMANDLINE:
                    builder.set(name, kwargs[name])
                else:
                    builder.setdefault(name, kwargs[name])
                kwargs.pop(name)
            return f(ctx, **kwargs)

        return typing.cast(Callable[P, R], inner)


class SklandGroup(Mixin, click.RichGroup):
    def __init__(self, default_command: str | None = None, **kwargs):
        """
        在设置了 default command 的情况下传入其他必要的参数
        以支持在不传入任何 command 的时候解析到 default command
        但需要注意的是，原命令中仍然需要写
        if ctx.invoked_subcommand is None:
            ctx.invoke(default_command_func)
        因为如果不加任何其它参数时，不会触发 resolve_command
        """
        self.default_command = default_command
        if default_command:
            kwargs["invoke_without_command"] = True
            kwargs.setdefault("context_settings", {})
            kwargs["context_settings"]["ignore_unknown_options"] = True

        super().__init__(**kwargs)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        """
        在设置了 default command 时重写 resolve_command
        当原本的 resolve_command 失败时，假装它找到了 default command，且没有消耗任何 args
        """
        if self.default_command is None:
            return super().resolve_command(ctx, args)

        # 保存 args 的副本，因为 resolve_command 失败时会修改原始列表
        preserved_args = args.copy()
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            # rich_click v1.9.5 及之前参数类型标注错误的 workaround
            ctx = typing.cast(click.RichContext, ctx)
            cmd = self.get_command(ctx, self.default_command)
            if cmd is None:
                ctx.fail(_("No such command {name!r}.").format(name=self.default_command))
            return self.default_command, cmd, preserved_args


def skland_group[**P, R](
    default_command: str | None = None, **kwargs
) -> Callable[MixinInput[P, R], SklandGroup]:
    return click.group(cls=SklandGroup, default_command=default_command, **kwargs)


class SklandCommand(Mixin, click.RichCommand):
    def __init__(self, **kwargs):
        callback = kwargs.get("callback")
        if callback is not None:
            kwargs["callback"] = self.wrap_ctx_obj(self.wrap_async(callback))
        super().__init__(**kwargs)

    @staticmethod
    def wrap_async[**P, R](f) -> CommandInput[P, R]:
        """
        将实际定义时的 (async) def command(global_option: GlobalOption, option1, option2, ...)
        转化成标准的同步格式
        def command(global_option: GlobalOption, **kwargs)
        如果原本是 async 的，使用 asyncio.run 包一层
        """
        if not inspect.iscoroutinefunction(f):
            return f

        @functools.wraps(f)
        def inner(global_option: GlobalOption, **kwargs) -> R:
            return asyncio.run(f(global_option, **kwargs))

        return inner

    @staticmethod
    def wrap_ctx_obj[**P, R](f: CommandInput[P, R]) -> MixinInput[P, R]:
        """
        将实际定义时的 def command(global_option: GlobalOption, option1, option2, ...)
        转化成 Mixin 的标准格式
        def command(ctx: click.Context, **kwargs)
        然后将 ctx.obj 中的 global option builder 取出，调用 build，放进第一个参数
        然后将剩余的 kwargs 原样转发给原本的 command
        """

        @functools.wraps(f)
        def inner(ctx: click.Context, **kwargs) -> R:
            builder = ctx.ensure_object(GlobalOptionBuilder)
            return f(builder.build(), **kwargs)

        return inner


def skland_command[**P, R](**kwargs) -> Callable[CommandInput[P, R], SklandCommand]:
    return click.command(cls=SklandCommand, **kwargs)
