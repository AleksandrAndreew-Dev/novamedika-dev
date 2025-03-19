# Используем базовый образ Python
FROM python:3.9-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1
ENV PYTHONPATH=/code


# Устанавливаем рабочую директорию
WORKDIR /code

# Устанавливаем системные зависимости и обновляем pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

# Копируем файл с зависимостями
COPY requirements.txt /code/

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . /code/

# Копируем конфигурацию Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Команда запуска Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "mysite.wsgi:application"]

