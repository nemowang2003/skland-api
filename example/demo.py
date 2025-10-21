from skland_api.auth_info import SklandAuthInfo
from skland_api.cli.constants import AUTH_FILE

import json

with open(AUTH_FILE, mode="r", encoding="utf-8") as fp:
    auth_data: dict = json.load(fp)
info = auth_data.get("nemo")
auth_info = SklandAuthInfo(**info)
api = auth_info.full_auth()
uid = api.binding_list()[0]["uid"]
print(api.cultivate(uid))
