import platformdirs

DEFAULT_MODULES = [
    "title",
    "sign",
    "online",
    "stamina",
    "affair",
    "base",
    "mission",
    "recruit",
    "interactive",
]

CACHE_DIR = platformdirs.user_cache_path("skland-api")
CACHE_DIR.mkdir(exist_ok=True)
LOG_FILE = CACHE_DIR / "skland-api.log"

ITEM_MAPPING: dict[str, str]

CONFIG_DIR = platformdirs.user_config_path("skland-api")
CONFIG_DIR.mkdir(exist_ok=True)
AUTH_FILE = CONFIG_DIR / "auth.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

OPERATOR_MAPPING_FIX = {
    "char_1001_amiya2": "阿米娅(近卫)",
    "char_1037_amiya3": "阿米娅(医疗)",
}


def __getattr__(name):
    if name == "ITEM_MAPPING":
        global ITEM_MAPPING
        import json
        import time

        ITEM_FILE = CACHE_DIR / "item_mapping.json"
        if (
            not ITEM_FILE.exists()
            or time.time() - ITEM_FILE.stat().st_mtime > 7 * 24 * 60 * 60
        ):
            import requests

            try:
                response = requests.get("https://backend.yituliu.cn/item/value").json()
                if response["code"] == 200:
                    ITEM_MAPPING = {
                        entry["itemId"]: entry["itemName"] for entry in response["data"]
                    }
                    with ITEM_FILE.open(mode="w", encoding="utf-8") as fp:
                        json.dump(ITEM_MAPPING, fp, ensure_ascii=False, indent=2)
                    return ITEM_MAPPING
            except Exception:
                pass

        with ITEM_FILE.open(mode="r", encoding="utf-8") as fp:
            ITEM_MAPPING = json.load(fp)
        return ITEM_MAPPING
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
