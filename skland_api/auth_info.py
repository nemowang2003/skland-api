from dataclasses import asdict, dataclass

from loguru import logger

from .api import SklandApi, SklandApiException


@dataclass(kw_only=True, slots=True)
class SklandAuthInfo:
    phone: str | None = None
    password: str | None = None
    token: str | None = None
    cred: str | None = None

    def __post_init__(self):
        if self.phone is not None:
            if len(self.phone) != 11 or not self.phone.isdigit():
                raise ValueError("手机号格式不正确（应为 11 位数字）")

        if self.token is not None and len(self.token) != 24:
            raise ValueError("Token 长度不正确（应为 24 位）")

        if self.cred is not None and len(self.cred) != 32:
            raise ValueError("Cred 长度不正确（应为 32 位）")

        if bool(self.phone) ^ bool(self.password):
            raise ValueError("请同时提供手机号和密码")

        if not any((self.phone, self.password, self.token, self.cred)):
            raise ValueError("请至少提供一项有效的认证信息")

    def to_dict(self) -> dict:
        return asdict(self)

    async def full_auth(self) -> SklandApi:
        api = SklandApi()
        if self.cred is not None:
            try:
                await api.set_cred(self.cred)
                return api
            except SklandApiException:
                logger.warning("failed to get auth from cred")

        if self.token is not None:
            try:
                self.cred = await api.cred_from_token(self.token)
                return api
            except SklandApiException:
                logger.warning("failed to get auth from token")

        if self.phone is not None and self.password is not None:
            try:
                self.token = await api.token_from_phone_password(self.phone, self.password)
                self.cred = await api.cred_from_token(self.token)
                return api
            except SklandApiException as e:
                logger.error(f"failed to get auth from phone and password: {e}")

        raise ValueError("all provided information failed to auth")
