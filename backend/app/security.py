"""Session cookies and at-rest encryption for GitHub tokens.

The browser only ever holds a signed session id. The GitHub access token is
encrypted with a key derived from SESSION_SECRET and never appears in any
response body, log line or Pydantic schema.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, URLSafeSerializer

from .config import get_settings

SESSION_COOKIE = "contribai_session"
STATE_COOKIE = "contribai_oauth_state"


@lru_cache
def _fernet() -> Fernet:
    secret = get_settings().session_secret.encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret).digest()))


@lru_cache
def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt="contribai-session")


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def make_session(user_id: int) -> str:
    return _serializer().dumps({"uid": user_id})


def read_session(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        data = _serializer().loads(raw)
    except BadSignature:
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return uid if isinstance(uid, int) else None


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)


def states_match(expected: str | None, received: str | None) -> bool:
    if not expected or not received:
        return False
    return secrets.compare_digest(expected, received)
