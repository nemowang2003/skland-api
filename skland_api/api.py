import hashlib
import hmac
import json
import requests
import time
import urllib.parse

APP_CODE = "4ca99fa6b56cc2ba"  # magic code


class SklandApiException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __str__(self):
        return f"{self.__class__.__name__}: ({self.code}) {self.msg}"


class SklandClient:
    def __init__(self):
        self.token = None
        self.headers = {
            "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0",
            "Accept-Encoding": "gzip",
            "Connection": "close",
        }

    @staticmethod
    def sign(path: str, token: str, payload: str) -> dict:
        timestamp = str(int(time.time()))
        payload_to_sign = "".join(
            [
                path,
                payload,
                timestamp,
                '{"platform":"","timestamp":"',
                timestamp,
                '","dId":"","vName":""}',
            ]
        )
        encrypted = hmac.new(
            token.encode("utf-8"),
            payload_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        sign = hashlib.md5(encrypted.encode("utf-8")).hexdigest()
        return {
            "sign": sign,
            "platform": "",
            "timestamp": timestamp,
            "dId": "",
            "vName": "",
        }

    @property
    def cred(self):
        return self.headers.get("cred")

    @cred.setter
    def cred(self, cred: str):
        self.headers = {"cred": cred} | self.headers

    @cred.deleter
    def cred(self):
        self.headers.pop("cred", default=None)

    def get(self, url, **kwargs):
        if self.token is not None:
            parse_result = urllib.parse.urlparse(url)
            path = parse_result.path
            payload = parse_result.query
            self.headers |= self.sign(path, self.token, payload)
        response = requests.get(url, headers=self.headers, **kwargs)
        try:
            response = response.json()
        except json.JSONDecodeError:
            return response.text
        code = response.get("status", 0) or response.get("code", 0)
        if code != 0:
            raise SklandApiException(
                code=code,
                msg=response.get("msg") or response.get("message", ""),
            )
        return response

    def post(self, url, **kwargs):
        if self.token is not None:
            path = urllib.parse.urlparse(url).path
            payload = kwargs.get("data") or json.dumps(kwargs.get("json", dict()))
            self.headers |= self.sign(path, self.token, payload)
        response = requests.post(url, headers=self.headers, **kwargs)
        try:
            response = response.json()
        except json.JSONDecodeError:
            return response.text
        code = response.get("status", 0) or response.get("code", 0)
        if code != 0:
            raise SklandApiException(
                code=code,
                msg=response.get("msg") or response.get("message", ""),
            )
        return response


class SklandApi:
    def __init__(self):
        self.client = SklandClient()

    def token_from_phone_password(self, phone: str, password: str) -> str:
        response = self.client.post(
            "https://as.hypergryph.com/user/auth/v1/token_by_phone_password",
            json={
                "phone": phone,
                "password": password,
            },
        )
        return response["data"]["token"]

    def cred_from_token(self, token: str) -> str:
        response = self.client.post(
            "https://as.hypergryph.com/user/oauth2/v2/grant",
            json={
                "token": token,
                "appCode": APP_CODE,
                "type": 0,
            },
        )
        grant_code = response["data"]["code"]

        response = self.client.post(
            "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code",
            json={
                "code": grant_code,
                "kind": 1,
            },
        )
        data = response["data"]
        cred = self.client.cred = data["cred"]
        self.client.token = data["token"]
        return cred

    def set_cred(self, cred: str):
        self.client.cred = cred
        self.client.token = self.client.get(
            "https://zonai.skland.com/api/v1/auth/refresh"
        )["data"]["token"]

    def binding_list(self) -> list[dict]:
        response = self.client.get(
            "https://zonai.skland.com/api/v1/game/player/binding"
        )
        return [
            character
            for game in response["data"]["list"]
            for character in game["bindingList"]
        ]

    def cultivate(self, uid: str) -> dict:
        return self.client.get(
            f"https://zonai.skland.com/api/v1/game/cultivate/player?uid={uid}"
        )["data"]

    def player_info(self, uid: str) -> dict:
        return self.client.get(
            f"https://zonai.skland.com/api/v1/game/player/info?uid={uid}"
        )["data"]

    def daily_sign_info(self, uid: str) -> dict:
        return self.client.get(
            f"https://zonai.skland.com/api/v1/game/attendance?uid={uid}"
        )["data"]

    def do_daily_sign(self, uid: str) -> list[dict]:
        return self.client.post(
            "https://zonai.skland.com/api/v1/game/attendance",
            json={
                "gameId": 1,
                "uid": uid,
            },
        )["data"]["awards"]
