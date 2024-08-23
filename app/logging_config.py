# logging_config.py
from typing import Dict
from loguru import logger

# Определение путей к файлам логов
log_paths: Dict[str, str] = {
    "app": "/logs/app.json",
    "db": "/logs/db.json",
    "users": "/logs/users.json",
    "admins": "/logs/admins.json",
    "terminals": "/logs/terminals.json",
    "system": "/logs/system.json"
}

log = logger


# Функция для настройки логирования
def configure_logging():
    for log_type, path in log_paths.items():
        log.add(
            path,
            rotation="1 day",
            retention="7 days",
            level="DEBUG",
            serialize=True,  # Логирование в формате JSON
            enqueue=True,  # Асинхронное логирование
            backtrace=True,  # Полные трейсы ошибок
            diagnose=True,  # Подробная диагностика
            filter=lambda record, log_type=log_type: record["extra"].get("type") == log_type
        )
    print("logger was configured successfully")


configure_logging()
