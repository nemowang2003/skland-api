import asyncio
import json
from dataclasses import dataclass
from functools import cached_property, wraps
from pathlib import Path
from typing import Self

import typer
from loguru import logger

from skland_api import SklandAuthInfo

APPNAME = "skland-api"


@dataclass(kw_only=True)
class GlobalOptions:
    config_dir: Path
    cache_dir: Path

    @cached_property
    def auth(self) -> dict[str, dict]:
        with self.auth_file.open(encoding="utf-8") as fp:
            return json.load(fp)

    @cached_property
    def config(self) -> dict:
        with self.config_file.open(encoding="utf-8") as fp:
            return json.load(fp)

    @cached_property
    def names(self) -> list[str]:
        return list(self.auth.keys())

    @cached_property
    def modules(self) -> list[str]:
        from skland_api.cli.modules import default_modules

        return default_modules

    @cached_property
    def auth_file(self) -> Path:
        return self.config_dir / "auth.json"

    @cached_property
    def config_file(self) -> Path:
        return self.config_dir / "config.json"

    @cached_property
    def log_file(self) -> Path:
        return self.cache_dir / f"{APPNAME}.log"

    @classmethod
    def construct_with_fallback(
        cls,
        names: list[str] | None,
        modules: list[str] | None,
        config_dir: Path,
        auth_file: Path | None,
        config_file: Path | None,
        cache_dir: Path,
        log_file: Path | None,
    ) -> Self:
        instance = cls(
            config_dir=config_dir.expanduser(),
            cache_dir=cache_dir.expanduser(),
        )
        if auth_file is not None:
            instance.auth_file = auth_file.expanduser()
        if not instance.auth_file.exists():
            create_auth_file(instance.auth_file)
        if config_file is not None:
            instance.config_file = config_file.expanduser()
        if not instance.config_file.exists():
            create_config_file(instance.config_file)
        if log_file is not None:
            instance.log_file = log_file.expanduser()
        if names is not None:
            instance.names = names
        elif (config_names := instance.config.get("names")) is not None:
            instance.names = config_names
        unique_names = list(dict.fromkeys(instance.names))
        if instance.names != unique_names:
            logger.warning("Duplicate names found, duplicates will be ignored.")
            instance.names = unique_names
        if modules is not None:
            instance.modules = modules
        elif (config_modules := instance.config.get("modules")) is not None:
            instance.modules = config_modules
        unique_modules = list(dict.fromkeys(instance.modules))
        if instance.modules != unique_modules:
            logger.warning("Duplicate modules found, duplicates will be ignored.")
            instance.modules = unique_modules
        return instance


def create_auth_file(file: Path) -> None:
    while True:
        try:
            typer.echo(
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

            phone = typer.prompt("Phone Number [Recommended]", default="")
            password = typer.prompt("Password [Recommended]", default="")
            token = typer.prompt("Token", default="")
            cred = typer.prompt("Cred", default="")

            auth_info = SklandAuthInfo(
                phone=phone or None,
                password=password or None,
                token=token or None,
                cred=cred or None,
            )

            name = typer.prompt("Name for this account")

            with file.open("w", encoding="utf-8") as fp:
                json.dump(
                    {name: auth_info.to_dict()},
                    fp,
                    ensure_ascii=True,
                    indent=2,
                )

            typer.echo(f"Auth file created at: {file}", err=True)

        except ValueError as e:
            typer.echo(f"Invalid information: {e}", err=True)
        except (EOFError, KeyboardInterrupt):
            typer.echo("", err=True)
            raise typer.Abort()


def create_config_file(file: Path):
    from skland_api.cli.modules import default_modules

    with file.open("w", encoding="utf-8") as fp:
        json.dump(
            {"name": [], "modules": default_modules, "module-config": {}},
            fp,
            ensure_ascii=True,
            indent=2,
        )
    typer.echo(f"Config file created at: {file}", err=True)


def async_command(func):
    if not asyncio.iscoroutinefunction(func):
        raise ValueError(f"{func!r} is not async")

    @wraps(func)
    def inner(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return inner
