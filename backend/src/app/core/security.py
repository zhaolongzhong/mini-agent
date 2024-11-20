import string
import secrets
from typing import Any
from datetime import datetime, timezone, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import Settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(settings: Settings, subject: str | Any, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random password with the specified length.
    The password will contain a mix of uppercase and lowercase letters,
    digits, and punctuation.
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = "".join(secrets.choice(alphabet) for i in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and sum(c.isdigit() for c in password) >= 3
            and any(c in string.punctuation for c in password)
        ):
            return password
