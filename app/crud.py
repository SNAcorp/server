from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models
from passlib.context import CryptContext

from app.models import User
from app.schemas import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

"""async def update_user_role(db: AsyncSession, user: models.User, role: str):
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_status(db: AsyncSession, user: models.User, is_verified: bool):
    user.is_verified = is_verified
    await db.commit()
    await db.refresh(user)
    return user


async def block_user(db: AsyncSession, user: models.User):
    user.block_date = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def unblock_user(db: AsyncSession, user: models.User):
    user.block_date = None
    await db.commit()
    await db.refresh(user)
    return user

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Vinotech{% endblock %}</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    {% block link %}{% endblock %}
    <style>
        html, body {
            height: 100%;
            margin: 0;
            overflow-x: hidden;
        }
        body {
            display: flex;
            flex-direction: column;
        }
        main {
            flex: 1;
        }
        {% block style %}
        {% endblock %}
    </style>
</head>
<body>
    <header>
        <nav class="navbar navbar-expand-lg navbar-light bg-light">
            <a class="navbar-brand" href="/">Vinotech</a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav mr-auto">
                    <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
                    {% if current_user %}
                        <li class="nav-item"><a class="nav-link" href="/users/me">My Profile</a></li>
                        <li class="nav-item"><a class="nav-link" href="/terminals">Terminals</a></li>
                        <li class="nav-item"><a class="nav-link" href="/create-order">Create Order</a></li>
                        {% if current_user.is_admin %}
                        <li class="nav-item"><a class="nav-link" href="/manage-bottles">Manage Bottles</a></li>
                        <li class="nav-item"><a class="nav-link" href="/admin/panel">Admin Panel</a></li>
                        {% endif %}
                        {% if current_user.is_superuser %}
                        <li class="nav-item"><a class="nav-link" href="/manage-bottles">Manage Bottles</a></li>
                        <li class="nav-item"><a class="nav-link" href="/superadmin/panel">Superadmin Panel</a></li>
                        {% endif %}
                    {% else %}
                    <li class="nav-item"><a class="nav-link" href="/login">Login/Register</a></li>
                    {% endif %}
                </ul>
            </div>
        </nav>
    </header>
    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>
    <footer class="footer py-3 bg-light" style="margin-bottom: 0">
        <div class="container">
            <span class="text-muted">&copy; 2024 from S.N.A. for Dmitry Yudin</span>
        </div>
    </footer>
    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
</body>
</html>

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор пользователя
    email = Column(String, unique=True, index=True, nullable=False)  # Email пользователя, уникальный
    hashed_password = Column(String, nullable=False)  # Хэшированный пароль пользователя
    is_active = Column(Boolean, default=True)  # Флаг активности пользователя
    is_superuser = Column(Boolean, default=False)  # Флаг суперпользователя
    is_verified = Column(Boolean, default=False)  # Флаг подтверждения email
    role = Column(String, default="user")  # Роль пользователя: user, admin, superadmin
    first_name = Column(String, nullable=False)  # Имя пользователя
    last_name = Column(String, nullable=False)  # Фамилия пользователя
    middle_name = Column(String, nullable=True)  # Отчество пользователя
    phone_number = Column(String, nullable=False)  # Телефонный номер пользователя
    registration_date = Column(DateTime, default=datetime.utcnow)  # Дата регистрации пользователя
    block_date = Column(DateTime, nullable=True)  # Дата блокировки пользователя, null если не заблокирован

У нас есть модель юзера и функции представленные в файле crud.py 
Нужно реализовать html шаблон с наследованием от Base.html (представлена выше)  которая реализует панель суперадмина и нужно добавить функцию, чтобы админ мог подтвердить почту пользователя (потому что без подтверждения )"""


async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_unblocked_users(db: AsyncSession):
    result = await db.execute(select(User).where(User.is_active == True))
    return result.scalars().all()


async def get_blocked_users(db: AsyncSession):
    result = await db.execute(select(User).where(User.is_active == False))
    return result.scalars().all()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        phone_number=user.phone_number
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_unverified_users(db: AsyncSession):
    result = await db.execute(select(User).where(User.is_verified == False))
    return result.scalars().all()


async def hash_func(word: str) -> str:
    return pwd_context.hash(word)


async def update_user_role(db: AsyncSession, user: models.User, role: str):
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_status(db: AsyncSession, user: models.User, is_verified: bool):
    user.is_verified = is_verified
    await db.commit()
    await db.refresh(user)
    return user


async def block_user(db: AsyncSession, user: models.User):
    user.block_date = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def unblock_user(db: AsyncSession, user: models.User):
    user.block_date = None
    await db.commit()
    await db.refresh(user)
    return user
