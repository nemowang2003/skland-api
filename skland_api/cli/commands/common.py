import asyncio
import inspect
import json
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Self

import rich_click as click
from loguru import logger
from rich.panel import Panel
from rich.prompt import Prompt

from skland_api import SklandAuthInfo
from skland_api.cli.utils import console

APPNAME = "skland-api"


@dataclass(frozen=True, kw_only=True, slots=True)
class GlobalOptions:
    names: list[str]
    modules: list[str]
    cache_dir: Path
    auth_file: Path
    log_file: Path
    auth: dict
    config: dict

    def update_auth_file(self) -> None:
        with self.auth_file.open("w", encoding="utf-8") as fp:
            json.dump(self.auth, fp, ensure_ascii=True, indent=2)

    @classmethod
    def from_command_line_options(
        cls,
        names: list[str] | None,
        modules: list[str] | None,
        config_dir: Path,
        auth_file: Path | None,
        config_file: Path | None,
        cache_dir: Path,
        log_file: Path | None,
    ) -> Self:
        config_dir = config_dir.expanduser()

        if auth_file is not None:
            auth_file = auth_file.expanduser()
        else:
            auth_file = config_dir / "auth.json"
        if not auth_file.exists():
            create_auth_file(auth_file)
        with auth_file.open(encoding="utf-8") as fp:
            auth = json.load(fp)

        if config_file is not None:
            config_file = config_file.expanduser()
        else:
            config_file = config_dir / "config.json"
        if not config_file.exists():
            create_config_file(config_file)
        with config_file.open(encoding="utf-8") as fp:
            config = json.load(fp)

        cache_dir = cache_dir.expanduser()

        if log_file is not None:
            log_file = log_file.expanduser()
        else:
            log_file = cache_dir / f"{APPNAME}.log"

        if names is None:
            if (config_names := config.get("names")) is not None:
                names = config_names
            else:
                names = list(auth.keys())
        unique_names = list(dict.fromkeys(names))
        if names != unique_names:
            logger.warning("Duplicate names found, duplicates will be ignored.")
            names = unique_names

        if modules is None:
            if (config_modules := config.get("modules")) is not None:
                modules = config_modules
            else:
                from skland_api.modules import default_modules

                modules = default_modules
        unique_modules = list(dict.fromkeys(modules))
        if modules != unique_modules:
            logger.warning("Duplicate modules found, duplicates will be ignored.")
            modules = unique_modules

        return cls(
            names=names,
            modules=modules,
            cache_dir=cache_dir,
            auth_file=auth_file,
            log_file=log_file,
            auth=auth,
            config=config,
        )


def create_auth_file(file: Path) -> None:
    if file.exists():
        logger.error(f"File {file} already exists when calling create_auth_file.")
        raise FileExistsError(file)

    while True:
        try:
            console.print(
                Panel(
                    f"[bold]All fields will be stored in [red]PLAIN TEXT[/red] in:[/bold]\n"
                    f"  [underline]{file.absolute()}[/underline]\n"
                    "Anyone with access to this file can read them.\n\n"
                    "You must provide at least [bold cyan]ONE[/] of:\n"
                    " • Phone (11 digits) AND Password\n"
                    " • Token (len=24)\n"
                    " • Cred  (len=32)",
                    title="[bold red]⚠️  Security Warning & Setup[/]",
                    border_style="red",
                    expand=False,
                )
            )

            phone = Prompt.ask("Phone Number [dim](Recommended)[/]", default=None)

            password = Prompt.ask("Password     [dim](Recommended)[/]", password=True, default=None)

            token = Prompt.ask("Token", default=None)
            cred = Prompt.ask("Cred", default=None)

            auth_info = SklandAuthInfo(
                phone=phone,
                password=password,
                token=token,
                cred=cred,
            )

            name = Prompt.ask("Name for this account")

            with file.open("w", encoding="utf-8") as fp:
                json.dump(
                    {name: auth_info.to_dict()},
                    fp,
                    ensure_ascii=True,
                    indent=2,
                )

            console.print(f"[bold green]Auth file created successfully at:[/]\n  {file}")
            return

        except ValueError as e:
            console.print(f"[bold red]Invalid information:[/]\n  {e}")
            console.print("[yellow]Please try again...[/]\n")

        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold yellow]! Aborted by user.[/]")
            raise click.Abort()


def create_config_file(file: Path):
    if file.exists():
        logger.error(f"File {file} already exists when calling create_config_file.")
        raise FileExistsError(file)
    try:
        with file.open("w", encoding="utf-8") as fp:
            json.dump(
                {"names": None, "modules": None, "module-config": {}},
                fp,
                ensure_ascii=True,
                indent=2,
            )
        console.print(f"[bold green]Config file created at:[/]\n  {file}")

    except Exception as e:
        console.print(f"[bold red]Failed to create config file:[/]\n  {e}")
        raise click.Abort()


def async_command(func):
    if not inspect.iscoroutinefunction(func):
        raise ValueError(f"{func!r} is not async")

    @wraps(func)
    def inner(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return inner
