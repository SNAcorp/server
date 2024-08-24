import os
import jwt
from datetime import (datetime)

from fastapi import (HTTPException)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


def decode_terminal_token(token: str) -> dict:
    """
    Decode a terminal token and return its payload.

    Args:
        token (str): The token to decode.

    Returns:
        dict: The payload of the token.

    Raises:
        HTTPException: If the token is invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid token")


def create_terminal_token(terminal_id: int,
                          registration_date: datetime,
                          uid: str) -> str:
    """
    Create a terminal token.

    Args:
        terminal_id (int): The terminal ID.
        registration_date (datetime): The registration date.
        uid (str): The user ID.

    Returns:
        str: The generated token.
    """
    payload = {
        "terminal_id": terminal_id,
        "registration_date": registration_date.isoformat(),
        "uid": uid
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_terminal(token: str) -> dict:
    """
    Verify a terminal token and return its payload.

    Args:
        token (str): The token to verify.

    Returns:
        dict: The payload of the token.

    Raises:
        HTTPException: If the token is expired or invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Signature has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
