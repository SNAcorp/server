import aiofiles
import jwt
from passlib.context import (CryptContext)
from datetime import (timedelta)
import datetime
from app.logging_config import log
from fastapi import Request

from app.schemas import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PRIVATE_KEY_PATH = "private_key.pem"
PUBLIC_KEY_PATH = "public_key.pem"

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 540

PRIVATE_KEY = None
PUBLIC_KEY = None

SPECIAL_TOKEN = "sokdfw324r-vekrfm2-sdvm2f-vsokdkvs"

async def create_access_token(request: Request, current_user: User, data: dict, expires_delta: timedelta = None):
    if PRIVATE_KEY is None:
        await load_keys()

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "special_token": SPECIAL_TOKEN})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Token was created in {datetime.datetime.utcnow()}")
    return encoded_jwt


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def load_keys():
    global PRIVATE_KEY, PUBLIC_KEY
    async with aiofiles.open(PRIVATE_KEY_PATH, "r") as private_file:
        PRIVATE_KEY = await private_file.read()
    async with aiofiles.open(PUBLIC_KEY_PATH, "r") as public_file:
        PUBLIC_KEY = await public_file.read()
