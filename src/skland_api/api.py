import hashlib
import hmac
import json
import time
import urllib.parse
from collections.abc import Generator
from typing import Literal, Never

import httpx

APP_CODE = "4ca99fa6b56cc2ba"  # magic code


class SklandApiException(Exception):
    def __init__(self, code: int, msg: str, response: httpx.Response):
        self.code = code
        self.msg = msg
        self.response = response

    def __str__(self):
        url = urllib.parse.unquote(str(self.response.url))
        return f"[{self.response.request.method} {url}] ({self.code}) {self.msg}"


class SklandClientAuth(httpx.Auth):
    def __init__(self, token: str | None = None):
        self.token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        if not self.token:
            yield request
            return

        path = request.url.path

        if request.method == "GET":
            payload = request.url.query.decode("utf-8")
        else:
            payload = request.content.decode("utf-8")

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
            self.token.encode("utf-8"),
            payload_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        sign = hashlib.md5(encrypted.encode("utf-8")).hexdigest()
        request.headers.update(
            {
                "sign": sign,
                "platform": "",
                "timestamp": timestamp,
                "dId": "",
                "vName": "",
            }
        )
        yield request


class SklandClient:
    client: httpx.AsyncClient

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            auth=SklandClientAuth(),
            headers={
                "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0",
                "Accept-Encoding": "gzip",
                "Connection": "close",
            },
        )

    @property
    def cred(self) -> str | None:
        return self.client.headers.get("cred")

    @cred.setter
    def cred(self, cred: str):
        self.client.headers = httpx.Headers(
            {"cred": cred} | {k: v for k, v in self.client.headers.items() if k.lower() != "cred"}
        )

    @cred.deleter
    def cred(self):
        self.client.headers.pop("cred", None)

    @property
    def token(self) -> Never:
        raise AttributeError(f"cannot read attribute 'token' from {self.__class__.__name__!r}")

    @token.setter
    def token(self, token: str):
        self.client.auth = SklandClientAuth(token)

    async def request(self, method: Literal["GET", "POST"], url: str, **kwargs):
        response = await self.client.request(method, url, **kwargs)
        try:
            response = response.json()
        except json.JSONDecodeError:
            preview = response.text[:50].replace("\n", " ")
            raise SklandApiException(
                code=-1,
                msg=f"响应解析失败(非json): {preview}",
                response=response,
            ) from None
        code = response.get("status", 0) or response.get("code", 0)
        if code != 0:
            raise SklandApiException(
                code=code,
                msg=response.get("msg") or response.get("message", ""),
                response=response,
            )
        return response

    async def get(self, url: str, **kwargs) -> dict:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> dict:
        return await self.request("POST", url, **kwargs)


class SklandApi:
    def __init__(self):
        self.client = SklandClient()

    async def token_from_phone_password(self, phone: str, password: str) -> str:
        response = await self.client.post(
            "https://as.hypergryph.com/user/auth/v1/token_by_phone_password",
            json={
                "phone": phone,
                "password": password,
            },
        )
        return response["data"]["token"]

    async def cred_from_token(self, token: str) -> str:
        response = await self.client.post(
            "https://as.hypergryph.com/user/oauth2/v2/grant",
            json={
                "token": token,
                "appCode": APP_CODE,
                "type": 0,
            },
        )
        grant_code = response["data"]["code"]

        response = await self.client.post(
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

    async def set_cred(self, cred: str):
        self.client.cred = cred
        response = await self.client.get("https://zonai.skland.com/api/v1/auth/refresh")
        self.client.token = response["data"]["token"]

    async def binding_list(self) -> list[dict]:
        response = await self.client.get("https://zonai.skland.com/api/v1/game/player/binding")
        return [character for game in response["data"]["list"] for character in game["bindingList"]]

    async def cultivate(self, uid: str) -> dict:
        response = await self.client.get(
            f"https://zonai.skland.com/api/v1/game/cultivate/player?uid={uid}"
        )
        return response["data"]

    async def player_info(self, uid: str) -> dict:
        response = await self.client.get(
            f"https://zonai.skland.com/api/v1/game/player/info?uid={uid}"
        )
        return response["data"]

    async def get_daily_checkin_status(self, uid: str) -> dict:
        response = await self.client.get(
            f"https://zonai.skland.com/api/v1/game/attendance?uid={uid}"
        )
        return response["data"]

    async def execute_daily_checkin(self, uid: str) -> list[dict]:
        response = await self.client.post(
            "https://zonai.skland.com/api/v1/game/attendance",
            json={
                "gameId": 1,
                "uid": uid,
            },
        )
        return response["data"]["awards"]
