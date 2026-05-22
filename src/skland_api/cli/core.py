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
import tomlkit
from click import ClickException
from click.core import ParameterSource
from loguru import logger
from rich.console import Console

from skland_api.models import AuthInfo

APPNAME = "skland-api"
console = Console()


class AuthFailure(ClickException):
    pass


def get_auth_file(auth_dir: Path, username: str) -> Path:
    return auth_dir / f"{username}.json"


def load_auth_info(auth_dir: Path, username: str) -> AuthInfo:
    auth_file = get_auth_file(auth_dir, username)
    if not auth_file.exists():
        raise AuthFailure(f"用户 {username!r} 的认证文件不存在: {auth_file}")
    try:
        with auth_file.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, ValueError) as e:
        raise AuthFailure(f"用户 {username!r} 的认证文件读取失败: {e}")

    if not isinstance(data, dict):
        raise AuthFailure(f"用户 {username!r} 的认证文件格式错误")

    try:
        return AuthInfo(
            phone=data.get("phone"),
            password=data.get("password"),
            token=data.get("token"),
            cred=data.get("cred"),
        )
    except ValueError as e:
        raise AuthFailure(f"用户 {username!r} 的认证文件格式错误: {e}")


def save_auth_info(auth_dir: Path, username: str, auth_info: AuthInfo) -> None:
    auth_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    auth_file = get_auth_file(auth_dir, username)
    with auth_file.open(mode="w", encoding="utf-8") as fp:
        json.dump(auth_info.to_dict(), fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    auth_file.chmod(0o600)


def remove_auth_info(auth_dir: Path, username: str) -> bool:
    auth_file = get_auth_file(auth_dir, username)
    if not auth_file.exists():
        return False
    auth_file.unlink()
    return True


def list_auth_users(auth_dir: Path) -> set[str]:
    return {path.stem for path in auth_dir.glob("*.json") if path.is_file()}


@dataclass(frozen=True, kw_only=True, slots=True)
class GlobalOption:
    config_file: Path
    config_content: tomlkit.TOMLDocument
    cache_dir: Path
    log_file: Path
    auth_dir: Path

    def writeback(self):
        with self.config_file.open(mode="w", encoding="utf-8") as fp:
            fp.write(self.config_content.as_string())


@dataclass(slots=True)
class GlobalOptionBuilder:
    click_options: ClassVar = [
        click.RichOption(
            ["--cache-dir"],
            envvar="SKLAND_API_CACHE_DIR",
            show_envvar=True,
            type=click.Path(path_type=Path, file_okay=False, resolve_path=True),
            default=lambda: platformdirs.user_cache_path(APPNAME),
            help="缓存文件存放目录",
        ),
        click.RichOption(
            ["--config-file"],
            envvar="SKLAND_API_CONFIG_FILE",
            show_envvar=True,
            type=click.Path(path_type=Path, dir_okay=False, resolve_path=True),
            default=lambda: platformdirs.user_config_path(APPNAME) / f"{APPNAME}.toml",
            help=f"配置文件 ({APPNAME}.toml) 的路径",
        ),
        click.RichOption(
            ["--log-file"],
            envvar="SKLAND_API_LOG_FILE",
            show_envvar=True,
            type=click.Path(path_type=Path, dir_okay=False, resolve_path=True),
            help=f"日志文件 ({APPNAME}.log) 的路径",
        ),
    ]

    config_file: Path | None = None
    cache_dir: Path | None = None
    log_file: Path | None = None
    auth_dir: Path | None = None

    def set(self, k: str, v) -> None:
        setattr(self, k, v)

    def setdefault(self, k: str, v) -> None:
        if getattr(self, k) is None:
            setattr(self, k, v)

    @staticmethod
    def sync_auth_and_config(auth_dir: Path, config_content: tomlkit.TOMLDocument) -> bool:
        config_users = set(config_content.keys())
        auth_users = list_auth_users(auth_dir)

        only_in_config = sorted(config_users - auth_users)
        only_in_auth = sorted(auth_users - config_users)

        if only_in_config:
            logger.warning(
                f"config 中存在但 auth 中不存在的账号: {', '.join(repr(x) for x in only_in_config)}"
            )

        if only_in_auth:
            logger.warning(
                f"auth 中存在但 config 中不存在的账号: {', '.join(repr(x) for x in only_in_auth)}"
            )
            for username in only_in_auth:
                config_content[username] = tomlkit.table()
            return True

        return False

    def build(self) -> GlobalOption:
        if self.cache_dir is None:
            self.cache_dir = platformdirs.user_cache_path(APPNAME, ensure_exists=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file is None:
            self.config_file = (
                platformdirs.user_config_path(APPNAME, ensure_exists=True) / f"{APPNAME}.toml"
            )

        if self.log_file is None:
            self.log_file = self.cache_dir / f"{APPNAME}.log"

        if self.auth_dir is None:
            self.auth_dir = self.config_file.parent / "auth"

        self.auth_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        if not self.config_file.exists():
            self.config_file.touch(0o600)
            config_content = tomlkit.TOMLDocument()
        else:
            try:
                with self.config_file.open(encoding="utf-8") as fp:
                    config_content = tomlkit.parse(fp.read())
            except Exception as e:
                raise ClickException(f"配置文件解析失败: {self.config_file}: {e}") from e

        should_writeback = self.sync_auth_and_config(self.auth_dir, config_content)

        if should_writeback:
            with self.config_file.open(mode="w", encoding="utf-8") as fp:
                fp.write(config_content.as_string())

        return GlobalOption(
            config_file=self.config_file,
            config_content=config_content,
            cache_dir=self.cache_dir,
            log_file=self.log_file,
            auth_dir=self.auth_dir,
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
        如果原本是 async 的，使用 asyncio.run 包一层
        将实际定义时的 async def f(global_option: GlobalOption, **kwargs)
        转化成标准的同步格式 def f(global_option: GlobalOption, **kwargs)
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
            global_option = ctx.ensure_object(GlobalOptionBuilder).build()
            logger.add(global_option.log_file)
            return f(global_option, **kwargs)

        return inner


def skland_command[**P, R](**kwargs) -> Callable[CommandInput[P, R], SklandCommand]:
    return click.command(cls=SklandCommand, **kwargs)
