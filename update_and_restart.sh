#!/bin/sh
set -e

cd server

# Обновить код из репозитория
git pull

# Построить Docker образы
docker compose build

# Перезапустить контейнеры
docker compose up
