import os
import subprocess
from sqlalchemy import Column, DateTime, MetaData, Table
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.crud import get_unverified_users, get_all_users, get_blocked_users, get_unblocked_users
from app.dependencies import get_current_user, get_admin_user
from app.routers import auth, users, admin, superadmin
from app.jwt_auth import verify_terminal
from app.models import Base, EMPTY_BOTTLE_ID, RFID, OrderItem, OrderRFID, TerminalState, BottleUsageLog
from app.routers import terminals, orders, bottles, rfid

from fastapi import Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from app.models import Order, Terminal, Bottle
from app.database import get_db
from app.schemas import IsServerOnline, User
from datetime import timedelta, datetime
from sqlalchemy.sql import func
from app.database import DATABASE_URL

app = FastAPI()

# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
#
# engine = create_engine("postgresql://server:v9023aSH@db:5432/terminals", echo=True)
#
# # Создание соединения
# conn = engine.connect()
# conn.execute("commit")
#
# # Создание базы данных "terminals"
# conn.execute("CREATE DATABASE terminals")
#
# # Закрытие соединения
# conn.close()

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

app.include_router(terminals.router, prefix="/terminal", tags=["terminals"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(bottles.router, prefix="/bottles", tags=["bottles"])
app.include_router(rfid.router, prefix="/rfid", tags=["rfid"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(superadmin.router, prefix="/superadmin", tags=["superadmin"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        states = [
            "Active",
            "Broken",
            "Under Maintenance",
            "Updating",
            "Switched off",
            "Connection lost"
        ]
        result = await session.execute(select(Bottle).where(Bottle.id == EMPTY_BOTTLE_ID))
        empty_bottle = result.scalars().first()
        if empty_bottle is None:
            empty_bottle = Bottle(
                id=EMPTY_BOTTLE_ID,
                name="Empty Bottle",
                winery="N/A",
                rating_average=0.0,
                location="N/A",
                image_path300="images/empty300.png",
                image_path600="images/empty600.png",
                description="This is an empty slot.",
                wine_type="N/A",
                volume=0.0
            )
            session.add(empty_bottle)
        for state in states:
            status = await session.execute(select(TerminalState).where(TerminalState.state == state))
            if status.scalars().first() is None:
                new_state = TerminalState(state=state)
                session.add(new_state)
        await session.commit()


app_templates = Jinja2Templates(directory="app/templates")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    # Добавьте другие допустимые источники здесь
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/learning", response_class=HTMLResponse)
async def read_learn(request: Request):
    topics = [
        {
            "title": "HTTP и HTTPS запросы",
            "sections": [
                {
                    "subtitle": "Протокол HTTP: методы (GET, POST, PUT, DELETE и т.д.)",
                    "links": [
                        {"text": "Основы HTTP", "url": "https://developer.mozilla.org/ru/docs/Web/HTTP/Overview"},
                        {"text": "HTTP Methods", "url": "https://www.restapitutorial.com/lessons/httpmethods.html"},
                        {"text": "Разница между PUT и POST",
                         "url": "https://stackoverflow.com/questions/630453/put-vs-post-in-rest"}
                    ],
                    "projectIdea": "Создание простого REST API для управления списком задач (To-Do List)."
                },
                {
                    "subtitle": "Структура HTTP-запросов и ответов",
                    "links": [
                        {"text": "Структура HTTP-запросов и ответов",
                         "url": "https://developer.mozilla.org/ru/docs/Web/HTTP/Messages"},
                        {"text": "HTTP Message Structure",
                         "url": "https://www.tutorialspoint.com/http/http_message_structure.htm"}
                    ],
                    "projectIdea": "Реализация сервера, который обрабатывает и возвращает различные виды HTTP-запросов."
                },
                {
                    "subtitle": "Заголовки HTTP и их использование",
                    "links": [
                        {"text": "Заголовки HTTP", "url": "https://developer.mozilla.org/ru/docs/Web/HTTP/Headers"},
                        {"text": "HTTP Headers Overview",
                         "url": "https://www.ntu.edu.sg/home/ehchua/programming/webprogramming/HTTP_Basics.html"}
                    ],
                    "projectIdea": "Создание API, который использует различные заголовки для управления кэшированием и авторизацией."
                },
                {
                    "subtitle": "Принципы работы HTTPS: SSL/TLS",
                    "links": [
                        {"text": "Как работает HTTPS", "url": "https://habr.com/ru/post/141217/"},
                        {"text": "Understanding SSL/TLS", "url": "https://www.cloudflare.com/learning/ssl/what-is-ssl/"}
                    ],
                    "projectIdea": "Развертывание безопасного веб-сервера с использованием SSL-сертификатов."
                },
                {
                    "subtitle": "Сертификаты и их проверка",
                    "links": [
                        {"text": "Что такое SSL-сертификаты",
                         "url": "https://habr.com/ru/company/ua-hosting/blog/267405/"},
                        {"text": "How SSL Certificates Work",
                         "url": "https://www.digicert.com/how-ssl-certificates-work"}
                    ],
                    "projectIdea": "Настройка собственного сертификата для веб-сайта и проверка его правильной установки."
                }
            ]
        },
        {
            "title": "WebSocket",
            "sections": [
                {
                    "subtitle": "Принципы работы WebSocket",
                    "links": [
                        {"text": "Что такое WebSocket",
                         "url": "https://developer.mozilla.org/ru/docs/Web/API/WebSockets_API/Writing_WebSocket_servers"},
                        {"text": "Introduction to WebSockets",
                         "url": "https://www.tutorialspoint.com/websockets/index.htm"}
                    ],
                    "projectIdea": "Создание чата в реальном времени с использованием WebSocket."
                },
                {
                    "subtitle": "Отличия от HTTP",
                    "links": [
                        {"text": "HTTP vs WebSocket", "url": "https://habr.com/ru/post/240069/"},
                        {"text": "WebSocket vs HTTP", "url": "https://ably.com/concepts/websockets"}
                    ],
                    "projectIdea": "Сравнение производительности и ресурсов между WebSocket и HTTP для чата."
                },
                {
                    "subtitle": "Примеры использования WebSocket",
                    "links": [
                        {"text": "Использование WebSocket",
                         "url": "https://developer.mozilla.org/ru/docs/Web/API/WebSockets_API"},
                        {"text": "WebSocket Use Cases",
                         "url": "https://www.smashingmagazine.com/2018/02/simplified-websockets-example/"}
                    ],
                    "projectIdea": "Реализация системы уведомлений в реальном времени для веб-приложения."
                }
            ]
        },
        {
            "title": "Передача пакетов",
            "sections": [
                {
                    "subtitle": "TCP/IP модель",
                    "links": [
                        {"text": "Модель TCP/IP", "url": "https://www.opennet.ru/docs/RUS/tcpip/"},
                        {"text": "TCP/IP Model", "url": "https://www.geeksforgeeks.org/tcp-ip-model/"}
                    ],
                    "projectIdea": "Создание простого TCP-сервера и клиента для обмена сообщениями."
                },
                {
                    "subtitle": "Работа сетевых протоколов",
                    "links": [
                        {"text": "Протоколы сетей", "url": "https://losst.ru/protokoly-setej"},
                        {"text": "Network Protocols",
                         "url": "https://www.cisco.com/c/en/us/solutions/enterprise-networks/network-protocols.html"}
                    ],
                    "projectIdea": "Реализация простого сетевого эмулятора, который демонстрирует работу различных протоколов."
                },
                {
                    "subtitle": "Анализ сетевого трафика",
                    "links": [
                        {"text": "Анализ сетевого трафика", "url": "https://habr.com/ru/company/itsumma/blog/271109/"},
                        {"text": "Network Traffic Analysis",
                         "url": "https://www.varonis.com/blog/network-traffic-analysis"}
                    ],
                    "projectIdea": "Анализ трафика на локальном сервере с помощью Wireshark и представление результатов."
                }
            ]
        },
        {
            "title": "Работа с командной строкой",
            "sections": [
                {
                    "subtitle": "Основные команды и их использование",
                    "links": [
                        {"text": "Основные команды Linux", "url": "https://losst.ru/komandnaya-stroka-linux"},
                        {"text": "Linux Command Line Basics",
                         "url": "https://ubuntu.com/tutorials/command-line-for-beginners#1-overview"}
                    ],
                    "projectIdea": "Создание набора скриптов для автоматизации повседневных задач."
                },
                {
                    "subtitle": "Написание и запуск скриптов",
                    "links": [
                        {"text": "Написание bash-скриптов", "url": "https://habr.com/ru/post/358662/"},
                        {"text": "Writing Shell Scripts", "url": "https://www.shellscript.sh/"}
                    ],
                    "projectIdea": "Разработка скрипта для резервного копирования файлов и папок."
                },
                {
                    "subtitle": "Примеры bash-скриптов",
                    "links": [
                        {"text": "Примеры bash-скриптов", "url": "https://losst.ru/primeri-bash-scenariev"},
                        {"text": "Bash Script Examples",
                         "url": "https://www.cyberciti.biz/tips/linux-showcase-10-umask-examples.html"}
                    ],
                    "projectIdea": "Написание скрипта для мониторинга системных ресурсов и уведомления об их использовании."
                }
            ]
        },
        {
            "title": "Работа с Linux",
            "sections": [
                {
                    "subtitle": "Установка и настройка Linux",
                    "links": [
                        {"text": "Установка Linux", "url": "https://losst.ru/kak-ustanovit-linux"},
                        {"text": "Installing Linux",
                         "url": "https://ubuntu.com/tutorials/install-ubuntu-desktop#1-overview"}
                    ],
                    "projectIdea": "Развертывание собственного веб-сервера на базе Linux."
                },
                {
                    "subtitle": "Администрирование системы",
                    "links": [
                        {"text": "Администрирование Linux", "url": "https://habr.com/ru/company/ruvds/blog/450312/"},
                        {"text": "Linux System Administration",
                         "url": "https://linuxize.com/post/basic-linux-system-administration-tasks/"}
                    ],
                    "projectIdea": "Настройка системы мониторинга и логирования на Linux-сервере."
                },
                {
                    "subtitle": "Управление пользователями и правами доступа",
                    "links": [
                        {"text": "Управление пользователями в Linux",
                         "url": "https://losst.ru/upravlenie-polzovatelyami-v-linux"},
                        {"text": "Managing Users in Linux",
                         "url": "https://www.tecmint.com/manage-users-and-groups-in-linux/"}
                    ],
                    "projectIdea": "Создание и управление несколькими пользователями и группами на сервере."
                }
            ]
        },
        {
            "title": "Docker",
            "sections": [
                {
                    "subtitle": "Основы Docker: контейнеризация приложений",
                    "links": [
                        {"text": "Основы Docker", "url": "https://habr.com/ru/company/flant/blog/423275/"},
                        {"text": "Docker Basics", "url": "https://docs.docker.com/get-started/overview/"}
                    ],
                    "projectIdea": "Контейнеризация веб-приложения с использованием Docker."
                },
                {
                    "subtitle": "Docker-compose: управление многоконтейнерными приложениями",
                    "links": [
                        {"text": "Docker-compose", "url": "https://docs.docker.com/compose/"},
                        {"text": "Introduction to Docker Compose",
                         "url": "https://docs.docker.com/compose/gettingstarted/"}
                    ],
                    "projectIdea": "Создание многоконтейнерного приложения с использованием docker-compose."
                },
                {
                    "subtitle": "Различия между docker-compose и docker compose",
                    "links": [
                        {"text": "Docker compose v2", "url": "https://docs.docker.com/compose/cli-command/"},
                        {"text": "Docker Compose V2",
                         "url": "https://collabnix.com/docker-compose-v2-now-generally-available/"}
                    ],
                    "projectIdea": "Обновление старого проекта на docker-compose v1 до docker-compose v2."
                }
            ]
        },
        {
            "title": "Фреймворки и библиотеки",
            "sections": [
                {
                    "subtitle": "Pydantic: валидация данных",
                    "links": [
                        {"text": "Документация Pydantic", "url": "https://pydantic-docs.helpmanual.io/"},
                        {"text": "Introduction to Pydantic",
                         "url": "https://towardsdatascience.com/introduction-to-pydantic-1ef4a90556d8"}
                    ],
                    "projectIdea": "Создание API с использованием FastAPI и валидацией данных через Pydantic."
                },
                {
                    "subtitle": "SQLAlchemy: ORM для работы с базами данных",
                    "links": [
                        {"text": "Документация SQLAlchemy", "url": "https://docs.sqlalchemy.org/"},
                        {"text": "Introduction to SQLAlchemy", "url": "https://realpython.com/python-sqlalchemy/"}
                    ],
                    "projectIdea": "Разработка системы управления базой данных с использованием SQLAlchemy."
                },
                {
                    "subtitle": "Что такое ORM и зачем они нужны",
                    "links": [
                        {"text": "Что такое ORM", "url": "https://habr.com/ru/post/193380/"},
                        {"text": "Introduction to ORM",
                         "url": "https://www.fullstackpython.com/object-relational-mappers-orms.html"}
                    ],
                    "projectIdea": "Реализация простого блога с использованием ORM."
                }
            ]
        },
        {
            "title": "Базы данных",
            "sections": [
                {
                    "subtitle": "Реляционные базы данных: Postgres, MySQL",
                    "links": [
                        {"text": "Введение в PostgreSQL", "url": "https://www.postgresql.org/docs/"},
                        {"text": "Introduction to PostgreSQL",
                         "url": "https://www.tutorialspoint.com/postgresql/index.htm"},
                        {"text": "Введение в MySQL", "url": "https://dev.mysql.com/doc/"},
                        {"text": "Introduction to MySQL", "url": "https://www.tutorialspoint.com/mysql/index.htm"}
                    ],
                    "projectIdea": "Разработка системы учета товаров с использованием PostgreSQL и MySQL."
                },
                {
                    "subtitle": "Основные различия между Postgres и MySQL",
                    "links": [
                        {"text": "Сравнение PostgreSQL и MySQL", "url": "https://habr.com/ru/post/446302/"},
                        {"text": "PostgreSQL vs MySQL", "url": "https://db-engines.com/en/system/MySQL%3BPostgreSQL"}
                    ],
                    "projectIdea": "Сравнительный анализ производительности PostgreSQL и MySQL для большого набора данных."
                },
                {
                    "subtitle": "Основы работы с SQL",
                    "links": [
                        {"text": "Основы SQL", "url": "https://www.sql-ex.ru/learn_exercises.php"},
                        {"text": "SQL Basics", "url": "https://www.tutorialspoint.com/sql/index.htm"}
                    ],
                    "projectIdea": "Написание SQL-запросов для выборки, обновления и удаления данных в базе данных."
                },
                {
                    "subtitle": "Индексы и оптимизация запросов",
                    "links": [
                        {"text": "Оптимизация SQL-запросов", "url": "https://habr.com/ru/post/119008/"},
                        {"text": "Index Optimization", "url": "https://use-the-index-luke.com/"}
                    ],
                    "projectIdea": "Оптимизация запросов в базе данных для ускорения работы веб-приложения."
                }
            ]
        },
        {
            "title": "Построение архитектур",
            "sections": [
                {
                    "subtitle": "Архитектурные шаблоны (MVC, MVVM, микросервисы)",
                    "links": [
                        {"text": "Архитектурные шаблоны", "url": "https://habr.com/ru/post/490644/"},
                        {"text": "Software Architecture Patterns", "url": "https://martinfowler.com/architecture/"}
                    ],
                    "projectIdea": "Разработка веб-приложения с использованием архитектурного шаблона MVC."
                },
                {
                    "subtitle": "Проектирование RESTful API",
                    "links": [
                        {"text": "Проектирование RESTful API", "url": "https://habr.com/ru/post/483202/"},
                        {"text": "Designing RESTful APIs", "url": "https://restfulapi.net/"}
                    ],
                    "projectIdea": "Создание RESTful API для управления пользовательскими данными."
                },
                {
                    "subtitle": "Основы проектирования масштабируемых систем",
                    "links": [
                        {"text": "Масштабируемые системы", "url": "https://habr.com/ru/post/494202/"},
                        {"text": "Scalable System Design", "url": "https://www.youtube.com/watch?v=-W9F__D3oY4"}
                    ],
                    "projectIdea": "Проектирование системы, способной обрабатывать большое количество запросов."
                }
            ]
        },
        {
            "title": "Авторизация и аутентификация",
            "sections": [
                {
                    "subtitle": "Принципы аутентификации (Basic, OAuth, JWT)",
                    "links": [
                        {"text": "OAuth 2.0 и JWT", "url": "https://habr.com/ru/post/340146/"},
                        {"text": "OAuth 2.0 Overview", "url": "https://oauth.net/2/"},
                        {"text": "JWT Introduction", "url": "https://jwt.io/introduction/"}
                    ],
                    "projectIdea": "Внедрение аутентификации с использованием JWT в веб-приложении."
                },
                {
                    "subtitle": "Стратегии авторизации",
                    "links": [
                        {"text": "Авторизация и аутентификация", "url": "https://habr.com/ru/company/vk/blog/465691/"},
                        {"text": "Authorization Strategies",
                         "url": "https://www.csoonline.com/article/3242947/what-is-authorization-how-it-differs-from-authentication.html"}
                    ],
                    "projectIdea": "Реализация ролевой модели доступа для управления правами пользователей."
                },
                {
                    "subtitle": "Безопасность аутентификации",
                    "links": [
                        {"text": "Безопасность аутентификации", "url": "https://habr.com/ru/company/vk/blog/465691/"},
                        {"text": "Authentication Security",
                         "url": "https://owasp.org/www-project-authentication-cheat-sheet/"}
                    ],
                    "projectIdea": "Внедрение многофакторной аутентификации для повышения безопасности приложения."
                }
            ]
        },
        {
            "title": "Куки и их принципы",
            "sections": [
                {
                    "subtitle": "Работа с куками",
                    "links": [
                        {"text": "Работа с куками", "url": "https://developer.mozilla.org/ru/docs/Web/HTTP/Cookies"},
                        {"text": "Cookies Overview", "url": "https://www.allaboutcookies.org/"}
                    ],
                    "projectIdea": "Управление сессиями пользователей с использованием куки."
                },
                {
                    "subtitle": "Сессионные куки и их использование",
                    "links": [
                        {"text": "Сессионные куки", "url": "https://www.tutorialspoint.com/http/http_cookies.htm"},
                        {"text": "Session Cookies", "url": "https://www.techopedia.com/definition/23572/session-cookie"}
                    ],
                    "projectIdea": "Реализация системы авторизации на основе сессионных куки."
                },
                {
                    "subtitle": "Безопасность куков",
                    "links": [
                        {"text": "Безопасность куков", "url": "https://habr.com/ru/post/437512/"},
                        {"text": "Cookie Security",
                         "url": "https://owasp.org/www-community/controls/SecureCookieAttribute"}
                    ],
                    "projectIdea": "Защита куков от XSS и CSRF атак в веб-приложении."
                }
            ]
        },
        {
            "title": "Кибер атаки и уязвимости",
            "sections": [
                {
                    "subtitle": "Основные виды кибер атак (SQL Injection, XSS, CSRF и т.д.)",
                    "links": [
                        {"text": "Виды кибер атак", "url": "https://owasp.org/www-project-top-ten/"},
                        {"text": "Common Cyber Attacks",
                         "url": "https://www.csoonline.com/article/3237324/top-cybersecurity-threats.html"}
                    ],
                    "projectIdea": "Создание веб-приложения с имитацией различных атак для обучения."
                },
                {
                    "subtitle": "Методы предотвращения атак",
                    "links": [
                        {"text": "Методы предотвращения атак", "url": "https://habr.com/ru/post/244991/"},
                        {"text": "Preventing Cyber Attacks",
                         "url": "https://www.csoonline.com/article/3237325/how-to-prevent-cyber-attacks.html"}
                    ],
                    "projectIdea": "Внедрение защиты от XSS и CSRF в существующее веб-приложение."
                },
                {
                    "subtitle": "Обзор известных уязвимостей",
                    "links": [
                        {"text": "Известные уязвимости", "url": "https://www.cvedetails.com/"},
                        {"text": "Common Vulnerabilities", "url": "https://nvd.nist.gov/"}
                    ],
                    "projectIdea": "Анализ уязвимостей известных веб-приложений и разработка мер по их устранению."
                }
            ]
        },
        {
            "title": "Исполняемый код скриптов на стороне сервера",
            "sections": [
                {
                    "subtitle": "Написание и выполнение .sh файлов",
                    "links": [
                        {"text": "Написание bash-скриптов", "url": "https://habr.com/ru/post/358662/"},
                        {"text": "Writing Shell Scripts", "url": "https://www.shellscript.sh/"}
                    ],
                    "projectIdea": "Автоматизация развертывания приложения с помощью bash-скриптов."
                },
                {
                    "subtitle": "Основные команды в скриптах",
                    "links": [
                        {"text": "Команды bash-скриптов", "url": "https://losst.ru/primeri-bash-scenariev"},
                        {"text": "Bash Command Cheat Sheet", "url": "https://devhints.io/bash"}
                    ],
                    "projectIdea": "Создание скрипта для автоматического обновления и перезапуска сервера."
                },
                {
                    "subtitle": "Примеры полезных скриптов",
                    "links": [
                        {"text": "Полезные bash-скрипты", "url": "https://losst.ru/primeri-bash-scenariev"},
                        {"text": "Useful Shell Scripts",
                         "url": "https://www.linuxshelltips.com/useful-linux-bash-scripts/"}
                    ],
                    "projectIdea": "Написание скрипта для мониторинга и уведомления о состоянии сервера."
                }
            ]
        },
        {
            "title": "Сервисы для очередей и распределенных задач",
            "sections": [
                {
                    "subtitle": "Kafka: система обмена сообщениями",
                    "links": [
                        {"text": "Введение в Kafka", "url": "https://habr.com/ru/company/epam_systems/blog/485238/"},
                        {"text": "Introduction to Kafka", "url": "https://kafka.apache.org/documentation/"}
                    ],
                    "projectIdea": "Реализация системы логирования с использованием Apache Kafka."
                },
                {
                    "subtitle": "Celery: распределенная система задач",
                    "links": [
                        {"text": "Документация Celery", "url": "https://docs.celeryproject.org/"},
                        {"text": "Introduction to Celery",
                         "url": "https://realpython.com/asynchronous-tasks-with-django-and-celery/"}
                    ],
                    "projectIdea": "Создание системы отложенных задач и планировщика с использованием Celery."
                }
            ]
        },
        {
            "title": "Микросервисы",
            "sections": [
                {
                    "subtitle": "Принципы построения микросервисной архитектуры",
                    "links": [
                        {"text": "Что такое микросервисы", "url": "https://habr.com/ru/post/432868/"},
                        {"text": "Microservices Architecture",
                         "url": "https://martinfowler.com/articles/microservices.html"}
                    ],
                    "projectIdea": "Разработка простого микросервисного приложения для управления пользователями."
                },
                {
                    "subtitle": "Преимущества и недостатки",
                    "links": [
                        {"text": "Преимущества микросервисов", "url": "https://habr.com/ru/post/432868/"},
                        {"text": "Advantages and Disadvantages of Microservices",
                         "url": "https://www.bmc.com/blogs/microservices-architecture/"}
                    ],
                    "projectIdea": "Анализ и демонстрация масштабируемости микросервисной архитектуры."
                },
                {
                    "subtitle": "Шаблоны проектирования микросервисов",
                    "links": [
                        {"text": "Шаблоны проектирования микросервисов", "url": "https://habr.com/ru/post/273003/"},
                        {"text": "Microservices Design Patterns",
                         "url": "https://www.toptal.com/software/microservices-architecture-tutorial"}
                    ],
                    "projectIdea": "Реализация шаблонов микросервисов для общего микросервисного приложения."
                },
                {
                    "subtitle": "Оркестрация микросервисов",
                    "links": [
                        {"text": "Оркестрация микросервисов", "url": "https://habr.com/ru/company/otus/blog/437612/"},
                        {"text": "Microservices Orchestration",
                         "url": "https://www.redhat.com/en/topics/microservices/what-is-microservices-orchestration"}
                    ],
                    "projectIdea": "Настройка Kubernetes для управления микросервисами."
                },
                {
                    "subtitle": "Инструменты для микросервисов (Docker, Kubernetes)",
                    "links": [
                        {"text": "Использование Docker и Kubernetes для микросервисов",
                         "url": "https://habr.com/ru/company/flant/blog/468079/"},
                        {"text": "Using Docker and Kubernetes for Microservices",
                         "url": "https://kubernetes.io/blog/2018/11/07/microservices-and-kubernetes/"}
                    ],
                    "projectIdea": "Развертывание микросервисов с использованием Docker и Kubernetes."
                }
            ]
        },
        {
            "title": "Дополнительные темы",
            "sections": [
                {
                    "subtitle": "Работа с REST API",
                    "links": [
                        {"text": "Принципы REST API", "url": "https://restfulapi.net/"},
                        {"text": "RESTful API Design", "url": "https://www.codecademy.com/articles/what-is-rest"}
                    ],
                    "projectIdea": "Создание REST API для управления библиотекой книг."
                },
                {
                    "subtitle": "Создание и тестирование REST API",
                    "links": [
                        {"text": "Создание REST API", "url": "https://habr.com/ru/post/505294/"},
                        {"text": "Building RESTful APIs", "url": "https://spring.io/guides/tutorials/rest/"}
                    ],
                    "projectIdea": "Написание тестов для REST API с использованием Postman."
                },
                {
                    "subtitle": "GraphQL",
                    "links": [
                        {"text": "Введение в GraphQL", "url": "https://graphql.org/learn/"},
                        {"text": "GraphQL Introduction", "url": "https://www.apollographql.com/docs/react/get-started/"}
                    ],
                    "projectIdea": "Создание API для блога с использованием GraphQL."
                },
                {
                    "subtitle": "Преимущества и недостатки по сравнению с REST",
                    "links": [
                        {"text": "GraphQL vs REST", "url": "https://habr.com/ru/post/441574/"},
                        {"text": "GraphQL vs REST Comparison",
                         "url": "https://www.apollographql.com/blog/graphql/basics/graphql-vs-rest/"}
                    ],
                    "projectIdea": "Анализ производительности и гибкости GraphQL по сравнению с REST."
                },
                {
                    "subtitle": "CI/CD",
                    "links": [
                        {"text": "Основы CI/CD", "url": "https://habr.com/ru/post/490574/"},
                        {"text": "CI/CD Overview", "url": "https://www.redhat.com/en/topics/devops/what-is-ci-cd"}
                    ],
                    "projectIdea": "Настройка CI/CD пайплайна для автоматической сборки и деплоя веб-приложения."
                },
                {
                    "subtitle": "Настройка CI/CD пайплайнов",
                    "links": [
                        {"text": "Настройка CI/CD", "url": "https://docs.gitlab.com/ee/ci/"},
                        {"text": "Setting Up CI/CD", "url": "https://circleci.com/docs/2.0/getting-started/"}
                    ],
                    "projectIdea": "Автоматизация тестирования и деплоя с использованием Jenkins или GitLab CI/CD."
                },
                {
                    "subtitle": "Облачные технологии",
                    "links": [
                        {"text": "Облачные технологии", "url": "https://aws.amazon.com/getting-started/"},
                        {"text": "Introduction to Cloud Computing",
                         "url": "https://azure.microsoft.com/en-us/overview/what-is-cloud-computing/"}
                    ],
                    "projectIdea": "Развертывание веб-приложения на AWS с использованием сервисов EC2 и S3."
                },
                {
                    "subtitle": "Контейнеризация и оркестрация (Kubernetes)",
                    "links": [
                        {"text": "Основы Kubernetes", "url": "https://kubernetes.io/docs/concepts/"},
                        {"text": "Kubernetes Introduction",
                         "url": "https://www.redhat.com/en/topics/containers/what-is-kubernetes"}
                    ],
                    "projectIdea": "Развертывание и управление контейнерами с помощью Kubernetes."
                },
                {
                    "subtitle": "Глубокий анализ пакетов (DPI)",
                    "links": [
                        {"text": "Принципы DPI", "url": "https://habr.com/ru/post/348836/"},
                        {"text": "Deep Packet Inspection", "url": "https://www.varonis.com/blog/deep-packet-inspection"}
                    ],
                    "projectIdea": "Реализация системы мониторинга сетевого трафика с использованием DPI."
                },
                {
                    "subtitle": "Применение DPI в сетевой безопасности",
                    "links": [
                        {"text": "DPI в сетевой безопасности", "url": "https://habr.com/ru/company/ruvds/blog/486234/"},
                        {"text": "DPI for Network Security",
                         "url": "https://www.csoonline.com/article/3250247/what-is-deep-packet-inspection-how-it-works-and-when-to-use-it.html"}
                    ],
                    "projectIdea": "Анализ и защита сетевого трафика от подозрительных пакетов."
                },
                {
                    "subtitle": "Инструменты для DPI",
                    "links": [
                        {"text": "Инструменты DPI", "url": "https://habr.com/ru/post/454266/"},
                        {"text": "DPI Tools", "url": "https://www.webtitan.com/deep-packet-inspection/"}
                    ],
                    "projectIdea": "Использование инструментов DPI для анализа трафика в реальном времени."
                },
                {
                    "subtitle": "Методы деплоя проектов",
                    "links": [
                        {"text": "Деплой веб-приложений", "url": "https://habr.com/ru/post/334066/"},
                        {"text": "Deploying Web Applications",
                         "url": "https://www.digitalocean.com/community/tutorial_series/getting-started-with-django-apps"}
                    ],
                    "projectIdea": "Деплой веб-приложения на облачный сервис с использованием CI/CD."
                },
                {
                    "subtitle": "Деплой контейнеров Docker",
                    "links": [
                        {"text": "Деплой контейнеров Docker", "url": "https://habr.com/ru/company/flant/blog/423275/"},
                        {"text": "Deploying Docker Containers", "url": "https://docs.docker.com/get-started/part3/"}
                    ],
                    "projectIdea": "Настройка автоматического деплоя Docker-контейнеров на сервере."
                },
                {
                    "subtitle": "Автоматизация деплоя с помощью CI/CD",
                    "links": [
                        {"text": "Автоматизация деплоя", "url": "https://docs.gitlab.com/ee/ci/"},
                        {"text": "CI/CD Deployment", "url": "https://circleci.com/docs/2.0/deployment-integrations/"}
                    ],
                    "projectIdea": "Создание CI/CD пайплайна для автоматического деплоя приложения после тестирования."
                },
                {
                    "subtitle": "Принципы анонимизации кода",
                    "links": [
                        {"text": "Анонимизация кода", "url": "https://habr.com/ru/post/491700/"},
                        {"text": "Code Anonymization",
                         "url": "https://www.oreilly.com/library/view/anonymizing-data/9781449311775/ch04.html"}
                    ],
                    "projectIdea": "Реализация системы анонимизации данных в веб-приложении."
                },
                {
                    "subtitle": "Инструменты для анонимизации кода",
                    "links": [
                        {"text": "Инструменты для анонимизации", "url": "https://habr.com/ru/company/vk/blog/467007/"},
                        {"text": "Data Anonymization Tools", "url": "https://www.guru99.com/anonymization-tools.html"}
                    ],
                    "projectIdea": "Использование инструментов для автоматической анонимизации данных."
                },
                {
                    "subtitle": "Примеры использования",
                    "links": [
                        {"text": "Примеры анонимизации кода", "url": "https://habr.com/ru/post/491700/"},
                        {"text": "Anonymization Examples",
                         "url": "https://dataprivacylab.org/dataprivacy/projects/kanonymity/index.html"}
                    ],
                    "projectIdea": "Реализация и тестирование различных методов анонимизации в проекте."
                },
                {
                    "subtitle": "Стратификация кода и построение современных сайтов",
                    "links": [
                        {"text": "Стратификация кода", "url": "https://habr.com/ru/post/462643/"},
                        {"text": "Code Layering",
                         "url": "https://martinfowler.com/articles/refactoring-code-layering.html"}
                    ],
                    "projectIdea": "Реализация стратифицированного архитектурного подхода в веб-приложении."
                },
                {
                    "subtitle": "Использование современных инструментов построения веба",
                    "links": [
                        {"text": "Современные инструменты веб-разработки",
                         "url": "https://habr.com/ru/company/otus/blog/492056/"},
                        {"text": "Modern Web Development Tools",
                         "url": "https://developer.mozilla.org/en-US/docs/Learn/Tools_and_testing/Understanding_client-side_tools/Introduction"}
                    ],
                    "projectIdea": "Создание современного веб-приложения с использованием React, Vue.js или Angular."
                },
                {
                    "subtitle": "Построение современных сайтов",
                    "links": [
                        {"text": "Построение современных сайтов",
                         "url": "https://habr.com/ru/company/ruvds/blog/436034/"},
                        {"text": "Building Modern Websites",
                         "url": "https://www.smashingmagazine.com/2020/02/building-modern-web-layouts-flexbox-css-grid/"}
                    ],
                    "projectIdea": "Создание респонсивного и SEO-оптимизированного сайта с использованием современных технологий."
                }
            ]
        },
        {
            "title": "Jinja2",
            "sections": [
                {
                    "subtitle": "Основы работы с Jinja2",
                    "links": [
                        {"text": "Jinja2 Documentation", "url": "https://jinja.palletsprojects.com/en/3.0.x/"},
                        {"text": "Introduction to Jinja2", "url": "https://realpython.com/primer-on-jinja-templating/"}
                    ],
                    "projectIdea": "Создание шаблонов для веб-приложения с использованием Jinja2."
                },
                {
                    "subtitle": "Примеры использования Jinja2",
                    "links": [
                        {"text": "Using Jinja2",
                         "url": "https://flask.palletsprojects.com/en/2.0.x/patterns/templateinheritance/"},
                        {"text": "Jinja2 Examples", "url": "https://pythonspot.com/jinja2/"}
                    ],
                    "projectIdea": "Реализация системы динамического создания HTML-страниц с помощью Jinja2."
                },
                {
                    "subtitle": "Расширенные возможности Jinja2",
                    "links": [
                        {"text": "Advanced Jinja2", "url": "https://jinja.palletsprojects.com/en/3.0.x/templates/"},
                        {"text": "Jinja2 Features",
                         "url": "https://realpython.com/primer-on-jinja-templating/#advanced-jinja2"}
                    ],
                    "projectIdea": "Создание сложных шаблонов с использованием макросов и фильтров Jinja2."
                }
            ]
        }
    ]
    return app_templates.TemplateResponse("lol.html", {"request": request, "topics": topics})


@app.get("/bottles", response_class=HTMLResponse)
async def list_bottles(request: Request, current_user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_db)):
    if current_user is None:
        return RedirectResponse("/login", 302)
    result = await session.execute(select(Bottle).filter(Bottle.id != -1))
    bottles = result.scalars().all()
    sorted_bottles = sorted(bottles, key=lambda x: x.id)
    return app_templates.TemplateResponse("bottle_list.html",
                                          {"request": request, "bottles": sorted_bottles, "current_user": current_user})


@app.get("/orders", response_class=HTMLResponse)
async def read_orders(request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)

    result = await db.execute(select(Order).options(selectinload(Order.items)))
    orders = result.scalars().all()

    return app_templates.TemplateResponse("orders.html",
                                          {"request": request,
                                           "orders": orders,
                                           "timedelta": timedelta,
                                           "current_user": current_user})


@app.post("/order/{order_id}/add_rfid")
async def add_rfid_to_order(order_id: int,
                            rfid_code: str = Form(...),
                            db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    rfid_result = await db.execute(select(RFID).where(RFID.code == rfid_code))
    rfid = rfid_result.scalars().first()
    if rfid is None:
        raise HTTPException(status_code=404, detail="RFID not found")

    order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
    db.add(order_rfid)
    await db.commit()

    return {"message": "RFID added to order successfully"}


@app.get("/login")
def admin_panel(request: Request,
                current_user: User = Depends(get_current_user)):
    if current_user:
        return RedirectResponse("/orders", 303)
    return app_templates.TemplateResponse("login_register.html",
                                          {"request": request})


@app.get("/order/{order_id}", response_class=HTMLResponse)
async def read_order(order_id: int, request: Request,
                     db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)

    result = await db.execute(
        select(Order).options(
            selectinload(Order.rfids).selectinload(OrderRFID.rfid),
            selectinload(Order.items).selectinload(OrderItem.bottle)
        ).where(Order.id == order_id)
    )
    order = result.scalars().first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверим, является ли order.items итерируемым объектом
    if not hasattr(order.items, '__iter__'):
        raise HTTPException(status_code=500, detail="Order items are not iterable")

    order_details = {
        "id": order.id,
        "is_completed": order.is_completed,
        "rfids": [{"code": order_rfid.rfid.code, "timestamp": order_rfid.timestamp} for order_rfid in order.rfids],
        "items": []
    }

    items = order.items
    print("items", items)

    return app_templates.TemplateResponse("order_detail.html",
                                          {"request": request,
                                           "order": order_details,
                                           "items": items,
                                           "current_user": current_user})


@app.get("/create-order", response_class=HTMLResponse)
async def create_order_page(request: Request,
                            current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    return app_templates.TemplateResponse("create_order.html",
                                          {"request": request,
                                           "current_user": current_user})


@app.post("/create-order", response_class=JSONResponse)
async def create_order(request: Request, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    data = await request.json()
    rfids = data.get('rfids', [])
    order = Order()
    db.add(order)
    await db.flush()  # Ensuring the order is added and its ID is available

    # Logging the received RFID codes for debugging
    print(f"Received RFID codes: {rfids}")

    errors = []
    for rfid_code in rfids:
        rfid_result = await db.execute(select(RFID).where(RFID.code == rfid_code))
        rfid = rfid_result.scalars().first()

        if rfid is None:
            # If RFID not found, add it to the database
            print(f"RFID {rfid_code} not found in the database. Adding it.")
            rfid = RFID(code=rfid_code)
            db.add(rfid)
            await db.flush()  # Ensure the RFID is added and its ID is available
        else:
            # Check if the RFID is in any active orders
            active_order_result = await db.execute(
                select(OrderRFID)
                    .join(Order)
                    .where(Order.is_completed == False, OrderRFID.rfid_id == rfid.id)
            )
            active_order_rfid = active_order_result.scalars().first()
            if active_order_rfid:
                errors.append({"rfid": rfid_code, "message": f"RFID {rfid_code} is already in use in an active order."})

        if not errors:
            order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
            db.add(order_rfid)

    if errors:
        return JSONResponse(content={"success": False, "errors": errors}, status_code=400)

    await db.commit()
    return JSONResponse(content={"success": True}, status_code=200)


@app.get("/terminals", response_class=HTMLResponse)
async def dashboard(request: Request,
                    db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    result = await db.execute(select(Terminal).options(selectinload(Terminal.status)))
    terminals = result.scalars().all()
    return app_templates.TemplateResponse("terminals.html",
                                          {"request": request,
                                           "terminals": terminals,
                                           "current_user": current_user})


@app.get("/", response_class=JSONResponse)
async def for_huckers():
    return {"msg": "Hello, how are you mr/mrs?) What are you need at this website?"}


@app.get("/static/{image_name}")
async def get_image(image_name: str):
    file_path = f"app/static/{image_name}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")


@app.get("/terminals/{terminal_id}", response_class=HTMLResponse)
async def manage_terminal(request: Request,
                          terminal_id: int,
                          db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    result = await db.execute(
        select(Terminal).options(selectinload(Terminal.bottles)).filter(Terminal.id == terminal_id))
    terminal = result.scalars().first()
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    bottles_result = await db.execute(select(Bottle))
    bottles = bottles_result.scalars().all()
    sorted_bottles = sorted(terminal.bottles, key=lambda x: x.slot_number)

    return app_templates.TemplateResponse("manage_terminal.html",
                                          {"request": request,
                                           "terminal": terminal,
                                           "bottles": bottles,
                                           "sorted": sorted_bottles,
                                           "current_user": current_user})



@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_admin_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    all_users = await get_all_users(db)
    unblocked_users = await get_unblocked_users(db)
    blocked_users = await get_blocked_users(db)
    unverified_users = []
    if current_user.is_superuser:
        unverified_users = await get_unverified_users(db)

    return app_templates.TemplateResponse("admin_panel.html", {
        "request": request,
        "current_user": current_user,
        "all_users": all_users,
        "unblocked_users": unblocked_users,
        "blocked_users": blocked_users,
        "unverified_users": unverified_users
    })


@app.post("/", response_class=JSONResponse)
async def reset_bottles_endpoint(request: IsServerOnline):
    payload = verify_terminal(request.token)
    if payload["terminal_id"] != request.terminal_id:
        raise HTTPException(status_code=403, detail="Invalid terminal ID")
    return {"is_online": True}


def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)


if __name__ == "__main__":
    main()
