#!/bin/sh
set -e

# Перейти в директорию проекта
cd /server

# Обновить код из репозитория
git pull

# Построить Docker образы
docker compose build

# Перезапустить контейнеры
docker compose up
