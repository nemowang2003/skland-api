from ..auth_info import SklandAuthInfo
from .constants import DEFAULT_MODULES, LOG_FILE, AUTH_FILE, CONFIG_FILE
from .character_info import CharacterInfo

import importlib
import json
import logging
import sys


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

stderr_handler = logging.StreamHandler()
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(stderr_handler)


file_handler = logging.FileHandler(filename=LOG_FILE, mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)


if not AUTH_FILE.exists():
    import getpass

    while True:
        try:
            print("add auth info for your first account!", file=sys.stderr)
            print("at least provide one piece of valid information", file=sys.stderr)
            print("(phone number and password together count as one)", file=sys.stderr)

            phone = input("Phone Number [Recommended]: ") or None
            password = getpass.getpass("Password [Recommended]: ") or None
            token = input("Token: ") or None
            cred = input("Cred: ") or None
            auth_info = SklandAuthInfo(
                phone=phone, password=password, token=token, cred=cred
            )
            name = input("Name for this account: ")
            break
        except ValueError as e:
            print(f"Invalid information: {e}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            exit()
    with AUTH_FILE.open(mode="w", encoding="utf-8") as fp:
        json.dump(
            {
                name: {
                    "phone": phone,
                    "password": password,
                    "token": token,
                    "cred": cred,
                }
            },
            fp,
        )

if not CONFIG_FILE.exists():
    with CONFIG_FILE.open(mode="w", encoding="utf-8") as fp:
        config = {
            "$schema": "",
            "names": [name],
            "modules": DEFAULT_MODULES,
        }
        json.dump(
            config,
            fp,
            ensure_ascii=False,
            indent=2,
        )
else:
    with CONFIG_FILE.open(mode="r", encoding="utf-8") as fp:
        config = json.load(fp)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--names")
    parser.add_argument("--modules")

    args = parser.parse_args()

    with open(AUTH_FILE, mode="r", encoding="utf-8") as fp:
        auth_data: dict = json.load(fp)
    for name in args.names.split(",") if args.names is not None else config["names"]:
        if (info := auth_data.get(name)) is None:
            logging.error("name '%s' is not recored", name)
            continue
        auth_info = SklandAuthInfo(**info)
        api = auth_info.full_auth()
        info.update(auth_info.as_dict())

        for character in api.binding_list():
            character_info = CharacterInfo(name, api, character)
            for module_name in (
                args.modules.split(",")
                if args.modules is not None
                else config["modules"]
            ):
                try:
                    module = importlib.import_module(
                        f".modules.{module_name}", package=__package__
                    )
                    module.handle(character_info)
                except ImportError:
                    logging.error("%s is not a valid module", module_name)
            print()

    with open(AUTH_FILE, mode="w", encoding="utf-8") as fp:
        json.dump(auth_data, fp, ensure_ascii=False, indent=2)
