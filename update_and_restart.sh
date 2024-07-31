#!/bin/sh
set -e

cd server

# Обновить код из репозитория
git pull

# Построить Docker образы
docker compose build

# Перезапустить контейнеры
docker compose up -d

# Подождать несколько секунд, чтобы убедиться, что контейнеры запустились
sleep 5

# Проверить состояние контейнеров
docker-compose ps