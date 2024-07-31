#!/bin/sh
set -e

# Обновить код из репозитория
git pull

# Построить Docker образы
docker compose build

# Перезапустить контейнеры
docker compose up
