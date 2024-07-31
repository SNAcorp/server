FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    gnupg \
    git \
    lsb-release \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY update_and_restart.sh /update_and_restart.sh
RUN chmod +x /update_and_restart.sh

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

RUN mkdir -p /images

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
