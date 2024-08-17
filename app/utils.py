from pathlib import Path
import aiofiles
import jwt
from passlib.context import (CryptContext)
from datetime import (datetime, timedelta)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PRIVATE_KEY_PATH = "private_key.pem"
PUBLIC_KEY_PATH = "public_key.pem"

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 540

PRIVATE_KEY = None
PUBLIC_KEY = None


async def create_access_token(data: dict, expires_delta: timedelta = None):
    if PRIVATE_KEY is None:
        await load_keys()

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def load_keys():
    global PRIVATE_KEY, PUBLIC_KEY
    async with aiofiles.open(PRIVATE_KEY_PATH, "r") as private_file:
        PRIVATE_KEY = await private_file.read()
    async with aiofiles.open(PUBLIC_KEY_PATH, "r") as public_file:
        PUBLIC_KEY = await public_file.read()
