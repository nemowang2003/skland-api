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

    def as_dict(self) -> dict:
        return asdict(self)

    def full_auth(self) -> SklandApi:
        api = SklandApi()
        if self.cred is not None:
            try:
                api.set_cred(self.cred)
                return api
            except SklandApiException as e:
                logging.warning(f"failed to get auth from cred: {e}")
        else:
            logging.warning("missing cred")

        if self.token is not None:
            try:
                self.cred = api.cred_from_token(self.token)
                return api
            except SklandApiException as e:
                logging.warning(f"failed to get auth from token: {e}")
        else:
            logging.warning("missing token")
        if self.phone is not None and self.password is not None:
            try:
                self.token = api.token_from_phone_password(self.phone, self.password)
                self.cred = api.cred_from_token(self.token)
                return api
            except SklandApiException as e:
                logging.warning(f"failed to get auth from phone and password: {e}")
        else:
            logging.error("missing phone and password, failed to auth")

        raise ValueError("all provided information failed to auth")
