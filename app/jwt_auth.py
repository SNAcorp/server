import jwt
from datetime import (datetime)

from fastapi import (HTTPException)
from fastapi.security import (HTTPBearer)

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
security = HTTPBearer()


def decode_terminal_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid token")


def create_terminal_token(terminal_id: int, registration_date: datetime, uid: str) -> str:
    payload = {
        "terminal_id": terminal_id,
        "registration_date": registration_date.isoformat(),
        "uid": uid
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_terminal(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Signature has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
