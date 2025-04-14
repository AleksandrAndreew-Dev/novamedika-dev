FROM python:3.10
WORKDIR /app

# Установка зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Устанавливаем PYTHONPATH
ENV PYTHONPATH=/app

# Собираем статические файлы
WORKDIR /app/mysite
RUN python manage.py collectstatic --noinput

# Запускаем Gunicorn с абсолютным путем
CMD ["gunicorn", "--timeout", "120", "--bind", "0.0.0.0:8000", "mysite.wsgi:application", "--chdir", "/app/mysite"]
