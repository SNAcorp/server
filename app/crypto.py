from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import os
import aiofiles

PRIVATE_KEY_PATH = "private_key.pem"
PUBLIC_KEY_PATH = "public_key.pem"


async def generate_rsa_keys(regenerate: bool = False):
    if not os.path.exists(PRIVATE_KEY_PATH) or not os.path.exists(PUBLIC_KEY_PATH) or regenerate is True:
        # Генерация приватного ключа
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Сохранение приватного ключа
        async with aiofiles.open(PRIVATE_KEY_PATH, "wb+") as private_file:
            await private_file.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()  # Без шифрования
                )
            )

        # Генерация публичного ключа
        public_key = private_key.public_key()

        # Сохранение публичного ключа
        async with aiofiles.open(PUBLIC_KEY_PATH, "wb+") as public_file:
            await public_file.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )

        print("Пара ключей сгенерирована и сохранена в файлы 'private_key.pem' и 'public_key.pem'")
    else:
        print("Ключи уже существуют, генерация не требуется.")
