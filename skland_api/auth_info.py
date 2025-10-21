from .api import SklandApi, SklandApiException

from dataclasses import asdict, dataclass
import logging


@dataclass(kw_only=True)
class SklandAuthInfo:
    phone: str | None = None
    password: str | None = None
    token: str | None = None
    cred: str | None = None

    def __post_init__(self):
        if self.phone is not None:
            if not isinstance(self.phone, str):
                raise TypeError("phone should be 'str'")
            if len(self.phone) != 11 or not all(char.isdigit() for char in self.phone):
                raise ValueError("invalid phone number (expected length: 11)")
        if self.password is not None:
            if not isinstance(self.password, str):
                raise TypeError("password should be 'str'")
        if self.token is not None:
            if not isinstance(self.token, str):
                raise TypeError("token should be 'str'")
            if len(self.token) != 24:
                raise ValueError("invalid token (expected length: 24)")
        if self.cred is not None:
            if not isinstance(self.cred, str):
                raise TypeError("cred should be 'str'")
            if len(self.cred) != 32:
                raise ValueError("invalid cred (expected length: 32)")
        if (self.phone or self.password) is not None and (
            self.phone and self.password
        ) is None:
            raise ValueError("must present phone and password at same time")
        if (self.phone or self.password or self.token or self.cred) is None:
            raise ValueError("must present at least one piece of valid information")

    def as_dict(self) -> dict:
        return asdict(self)

    def full_auth(self) -> SklandApi:
        api = SklandApi()
        if self.cred is not None:
            try:
                api.set_cred(self.cred)
                return api
            except SklandApiException as e:
                logging.warning("failed to get auth from cred: %s", e)
        else:
            logging.warning("missing cred")

        if self.token is not None:
            try:
                self.cred = api.cred_from_token(self.token)
                return api
            except SklandApiException as e:
                logging.warning("failed to get auth from token: %s", e)
        else:
            logging.warning("missing token")
        if self.phone is not None and self.password is not None:
            try:
                self.token = api.token_from_phone_password(self.phone, self.password)
                self.cred = api.cred_from_token(self.token)
                return api
            except SklandApiException as e:
                logging.warning("failed to get auth from phone and password: %s", e)
        else:
            logging.error("missing phone and password, failed to auth")
        raise ValueError("all provided information failed to auth")
