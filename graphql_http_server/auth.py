# middleware.py
import json
import logging
from functools import lru_cache
from threading import Timer
from urllib.request import urlopen

from authlib.jose.rfc7517.jwk import JsonWebKey, KeySet
from authlib.oauth2 import OAuth2Error, ResourceProtector
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from authlib.oauth2.rfc7523 import JWTBearerTokenValidator
from authlib.oauth2.rfc7523.validator import JWTBearerToken


from pydantic import BaseSettings, Field

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection, Request

logger = logging.getLogger(__name__)



class Settings(BaseSettings):
    secret_key: str = Field(title="Starlette SessionMiddleware Secret Key")
    oidc_issuer: str = Field(title="OIDC Issuer")
    oidc_audience: str = Field(title="OIDC Audience")

    class Config:
        env_file = ".env"

settings = Settings()


class RepeatTimer(Timer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.daemon = True

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class BearerTokenValidator(JWTBearerTokenValidator):
    def __init__(self, issuer: str, audience: str):
        self._issuer = issuer
        self._jwks_uri: str | None = None
        super().__init__(public_key=self.fetch_key(), issuer=issuer)
        self.claims_options = {
            "exp": {"essential": True},
            "aud": {"essential": True, "value": audience},
            "iss": {"essential": True, "value": issuer},
        }
        self._timer = RepeatTimer(3600, self.refresh)
        self._timer.start()

    def refresh(self):
        try:
            self.public_key = self.fetch_key()
        except Exception as exc:
            logger.warning(f"Could not update jwks public key: {exc}")

    def fetch_key(self) -> KeySet:
        """Fetch the jwks_uri document and return the KeySet."""
        response = urlopen(self.jwks_uri)
        logger.debug(f"OK GET {self.jwks_uri}")
        return JsonWebKey.import_key_set(json.loads(response.read()))

    @property
    def jwks_uri(self) -> str:
        """The jwks_uri field of the openid-configuration document."""
        if self._jwks_uri is None:
            config_url = urlopen(f"{self._issuer}/.well-known/openid-configuration")
            config = json.loads(config_url.read())
            self._jwks_uri = config["jwks_uri"]
        return self._jwks_uri


class BearerTokenAuthBackend(AuthenticationBackend):
    def __init__(self, issuer: str, audience: str) -> None:
        rp = ResourceProtector()
        validator = BearerTokenValidator(
            issuer=issuer,
            audience=audience,
        )
        rp.register_token_validator(validator)
        self.resource_protector = rp

    async def authenticate(self, conn: HTTPConnection):
        request = Request(conn.scope)
        try:
            token: JWTBearerToken = self.resource_protector.validate_request(
                scopes=["openid"],
                request=request,
            )
        except (MissingAuthorizationError, OAuth2Error) as error:
            raise AuthenticationError(error.description) from error
        scope: str = token.get_scope()
        scopes = scope.split()
        scopes.append("authenticated")
        return AuthCredentials(scopes=scopes), SimpleUser(username=token["email"])


middleware = [
    Middleware(
        AuthenticationMiddleware,
        backend=BearerTokenAuthBackend(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
        ),
    )
]