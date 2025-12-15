from dataclasses import asdict, dataclass

from loguru import logger

from .api import SklandApi, SklandApiException


@dataclass(kw_only=True)
class SklandAuthInfo:
    phone: str | None = None
    password: str | None = None
    token: str | None = None
    cred: str | None = None

    def __post_init__(self):
        if self.phone is not None:
            if len(self.phone) != 11 or not self.phone.isdigit():
                raise ValueError("invalid phone number (expected length: 11)")

        if self.token is not None and len(self.token) != 24:
            raise ValueError("invalid token (expected length: 24)")

        if self.cred is not None and len(self.cred) != 32:
            raise ValueError("invalid cred (expected length: 32)")

        if bool(self.phone) ^ bool(self.password):
            raise ValueError("phone and password must be provided together")

        if not any((self.phone, self.password, self.token, self.cred)):
            raise ValueError("must present at least one piece of valid information")

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
            except SklandApiException:
                logger.exception("failed to get auth from phone and password")

        raise ValueError("all provided information failed to auth")
