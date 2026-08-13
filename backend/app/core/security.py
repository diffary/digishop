from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    payload =  {
"sub": str(user_id),
"exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.InvalidTokenError,KeyError,ValueError ):
        return None
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
