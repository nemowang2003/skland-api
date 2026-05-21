from dataclasses import asdict, dataclass

from loguru import logger

from skland_api.api import SklandApi, SklandApiException


@dataclass(kw_only=True, slots=True)
class AuthInfo:
    phone: str | None = None
    password: str | None = None
    token: str | None = None
    cred: str | None = None

    def __post_init__(self):
        if bool(self.phone) ^ bool(self.password):
            raise ValueError("请同时提供手机号和密码")

        if not any((self.phone, self.password, self.token, self.cred)):
            raise ValueError("请至少提供一项有效的认证信息")

        if self.phone is not None:
            msg = self.check_phone(self.phone)
            if msg is not None:
                raise ValueError(msg)

        if self.token is not None:
            msg = self.check_token(self.token)
            if msg is not None:
                raise ValueError(msg)

        if self.cred is not None:
            msg = self.check_cred(self.cred)
            if msg is not None:
                raise ValueError(msg)

    @staticmethod
    def check_phone(phone: str) -> str | None:
        if len(phone) != 11 or not phone.isdigit():
            return "手机号格式不正确（应为 11 位数字）"

    @staticmethod
    def check_token(token: str) -> str | None:
        if token is not None and len(token) != 24:
            return "token 长度不正确（应为 24 位）"

    @staticmethod
    def check_cred(cred: str) -> str | None:
        if cred is not None and len(cred) != 32:
            return "cred 长度不正确（应为 32 位）"

    def to_dict(self) -> dict:
        return asdict(self)

    async def full_auth(self) -> SklandApi:
        api = SklandApi()
        if self.cred is not None:
            try:
                await api.set_cred(self.cred)
                return api
            except SklandApiException:
                logger.warning("使用 cred 认证失败")

        if self.token is not None:
            try:
                self.cred = await api.cred_from_token(self.token)
                return api
            except SklandApiException:
                logger.warning("使用 token 认证失败")

        if self.phone is not None and self.password is not None:
            try:
                self.token = await api.token_from_phone_password(self.phone, self.password)
                self.cred = await api.cred_from_token(self.token)
                return api
            except SklandApiException as e:
                logger.error(f"使用手机号与密码认证失败: {e}")

        raise ValueError("所有配置的认证信息都认证失败了")
