#!/Users/nemo/skland-api/.venv/bin/python3

from skland_api import SklandApiException
from skland_api.cli import AuthManager

from pathlib import Path

AUTH_FILE = Path.home() / ".config/skland-api/auth.json"
with AuthManager(AUTH_FILE) as auth_manager:
    for api in auth_manager.all_users_api():
        for character in api.binding_list():
            print(character["nickName"])
            uid = character["uid"]
            try:
                awards = api.daily_sign(uid)
                print(awards)
            except SklandApiException as e:
                print(e.msg)
