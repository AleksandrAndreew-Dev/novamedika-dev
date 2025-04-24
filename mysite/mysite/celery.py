from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Установите переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

app = Celery('mysite')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Используем DatabaseScheduler для хранения расписания в БД
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'
app.conf.timezone = 'UTC'
app.conf.update(
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Опционально: добавьте периодические задачи по умолчанию
@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    from pharmacies.documents import ProductDocument
    ProductDocument.init()

    # Создаем интервал (например, каждые 2 минуты)
    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.MINUTES,
    )

    # Создаем задачу для обновления Elasticsearch
    PeriodicTask.objects.get_or_create(
        interval=schedule,
        name='Update Elasticsearch every 2 minutes',
        task='pharmacies.tasks.update_elasticsearch_index',
    )

    # Пример ежедневной задачи в 3:00 UTC
    daily_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.DAYS,
    )

    PeriodicTask.objects.get_or_create(
        interval=daily_schedule,
        name='Full Elasticsearch resync daily',
        task='pharmacies.tasks.full_elasticsearch_resync',
    )
