from celery import shared_task
from django.utils import timezone
from elasticsearch import Elasticsearch, helpers
from .models import Order, Product
from .documents import ProductDocument
from elasticsearch.connection import RequestsHttpConnection




import requests
from django.core.cache import cache
from django.conf import settings
from .models import TelegramSubscriber

@shared_task
def check_telegram_updates():
    last_offset = cache.get('telegram_last_offset', 0)

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {
        "offset": last_offset + 1,
        "timeout": 30  # Long Polling (30 секунд)
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        if not data["ok"]:
            return

        for update in data["result"]:
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            command = message.get("text", "").lower()

            if command == "/start":
                TelegramSubscriber.objects.get_or_create(chat_id=chat_id)
            elif command == "/stop":
                TelegramSubscriber.objects.filter(chat_id=chat_id).delete()

            last_offset = max(last_offset, update["update_id"])

        cache.set('telegram_last_offset', last_offset)

    except Exception as e:
        print(f"Ошибка: {e}")





es_client = Elasticsearch(
    hosts=["http://elasticsearch-node-1:9200"],
    http_auth=("elastic", "elastic"),
    connection_class=RequestsHttpConnection,
    timeout=30,
    max_retries=10,
    retry_on_timeout=True
)

# Проверка соединения при старте
try:
    if not es_client.ping():
        raise ValueError("Cannot connect to Elasticsearch")
except Exception as e:
    print(f"Elasticsearch connection error: {str(e)}")


@shared_task
def order_created(order_uuid):
    from .models import Order, TelegramSubscriber
    import requests
    from django.conf import settings

    try:
        order = Order.objects.get(uuid=order_uuid)
        message = (
            f"🆕 *Новый заказ!*\n"
            f"🔖 Номер: `{order.uuid}`\n"
            f"👤 Клиент: {order.user_name} {order.user_surname}\n"
            f"📱 Телефон: `{order.user_phone}`\n"
            f"💊 Товар: {order.product_name} {order.product_form}\n"
            f"💰 Цена: {order.product_price} ₸\n"
            f"📦 Количество: {order.quantity}\n"
            f"🏥 Аптека: {order.pharmacy_name} (#{order.pharmacy_number})"
        )

        subscribers = TelegramSubscriber.objects.all()
        for sub in subscribers:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": sub.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            try:
                requests.post(url, json=payload)
            except Exception as e:
                print(f"Ошибка отправки: {e}")

    except Order.DoesNotExist:
        return False
    return True


@shared_task
def update_elasticsearch_index():
    """Частичное обновление индекса Elasticsearch для измененных продуктов"""
    es = es_client

    index_name = ProductDocument.Index.name
    chunk_size = 1000
    if not es.indices.exists(index=index_name):
        ProductDocument.init()

    last_update = timezone.now() - timezone.timedelta(minutes=2)
    products = Product.objects.filter(updated_at__gte=last_update).select_related('pharmacy')

    total_updated = 0
    for i in range(0, products.count(), chunk_size):
        chunk = products[i:i + chunk_size]
        actions = [
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": str(product.uuid),  # Используем UUID вместо ID
                "_source": ProductDocument().to_dict(product),
            }
            for product in chunk
        ]
        if actions:
            helpers.bulk(es, actions)
            total_updated += len(actions)

    if total_updated > 0:
        es.indices.refresh(index=index_name)

    return f"Updated {total_updated} products in Elasticsearch"


@shared_task
def full_elasticsearch_resync():
    """Полная синхронизация индекса Elasticsearch"""
    es = es_client
    index_name = ProductDocument.Index.name

    if not es.indices.exists(index=index_name):
        ProductDocument.init()

    products = Product.objects.all()
    total_resynced = 0
    chunk_size = 1000
    chunk = []
    for product in products:
        chunk.append(product)
        if len(chunk) == chunk_size:
            actions = [
                {
                    "_op_type": "index",
                    "_index": ProductDocument.Index.name,
                    "_id": str(product.uuid),  # Используем UUID вместо ID
                    "_source": ProductDocument().to_dict(product),
                }
                for product in chunk
            ]
            helpers.bulk(es, actions)
            chunk = []
            total_resynced += len(actions)

    if chunk:
        actions = [
            {
                "_op_type": "index",
                "_index": ProductDocument.Index.name,
                "_id": str(product.uuid),  # Используем UUID вместо ID
                "_source": ProductDocument().to_dict(product),
            }
            for product in chunk
        ]
        helpers.bulk(es, actions)
        total_resynced += len(actions)

    es.indices.refresh(index=index_name)
    return f"Resynced {total_resynced} products in Elasticsearch"


@shared_task
def update_pharmacy_city_in_index(pharmacy_name, pharmacy_number):
    from .models import Pharmacy, Product
    from .documents import ProductDocument

    es = es_client
    index_name = ProductDocument.Index.name

    if not es.indices.exists(index=index_name):
        ProductDocument.init()

    try:
        # Ищем аптеку по имени и номеру (оба параметра как строки)
        pharmacy = Pharmacy.objects.filter(
            name=pharmacy_name,
            pharmacy_number=str(pharmacy_number)  # Гарантируем строковый тип
        ).first()

        if not pharmacy:
            # Попробуем найти без учета регистра для имени
            pharmacy = Pharmacy.objects.filter(
                name__iexact=pharmacy_name,
                pharmacy_number=str(pharmacy_number)
            ).first()
            if not pharmacy:
                return f"Pharmacy '{pharmacy_name}' with number {pharmacy_number} not found."

        # Получаем продукты с select_related
        products = Product.objects.filter(pharmacy=pharmacy).select_related('pharmacy')

        if not products.exists():
            return f"No products found for pharmacy '{pharmacy.name}' (#{pharmacy.pharmacy_number})"

        # Подготовка данных для Elasticsearch
        actions = [{
            "_op_type": "index",
            "_index": index_name,
            "_id": str(product.uuid),
            "_source": ProductDocument().to_dict(product),
        } for product in products]

        # Пакетное обновление
        helpers.bulk(es, actions)
        es.indices.refresh(index=index_name)

        return f"Updated {len(actions)} products for pharmacy '{pharmacy.name}' (#{pharmacy.pharmacy_number})"

    except Exception as e:
        return f"Error updating products: {str(e)}"

def chunked(iterable, size):
    """Разбивает итерируемый объект на чанки заданного размера."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

@shared_task
def remove_pharmacy_products_from_index(pharmacy_uuid):
    """Удаляет все продукты аптеки из индекса"""
    from .models import Pharmacy
    from .documents import ProductDocument

    es = es_client
    index_name = ProductDocument.Index.name

    try:
        pharmacy = Pharmacy.objects.get(uuid=pharmacy_uuid)

        # Используем итератор для больших наборов данных
        product_uuids = pharmacy.products.values_list('uuid', flat=True).iterator()

        chunk_size = 1000
        actions = []

        # Формируем bulk-запросы
        for uuid_batch in chunked(product_uuids, chunk_size):
            for uuid in uuid_batch:
                actions.append({
                    "_op_type": "delete",
                    "_index": index_name,
                    "_id": str(uuid)
                })

            # Отправляем batch удалений
            helpers.bulk(es, actions)
            actions.clear()  # Очищаем список для следующего batch

        # Однократное обновление индекса
        es.indices.refresh(index=index_name)
        return f"Removed products for pharmacy {pharmacy_uuid}"

    except Pharmacy.DoesNotExist:
        return f"Pharmacy {pharmacy_uuid} not found"


@shared_task
def remove_products_from_index(product_uuids):
    """Удаляет продукты по их UUID из индекса"""
    es = es_client
    index_name = ProductDocument.Index.name

    if not product_uuids:
        return "No product UUIDs provided"

    if not es.indices.exists(index=index_name):
        return f"Index {index_name} does not exist"

    try:
        chunk_size = 1000
        for i in range(0, len(product_uuids), chunk_size):
            chunk = product_uuids[i:i + chunk_size]
            body = {
                "query": {
                    "terms": {
                        "_id": [str(uuid) for uuid in chunk]  # Преобразуем UUID в строки
                    }
                }
            }
            es.delete_by_query(index=index_name, body=body)

        es.indices.refresh(index=index_name)
        return f"Removed {len(product_uuids)} products from index"
    except Exception as e:
        return f"Error removing products: {str(e)}"


# В tasks.py добавьте обработку ошибок и прогрессивную индексацию
@shared_task
def bulk_update_elasticsearch(product_uuids):
    es = es_client
    index_name = ProductDocument.Index.name

    if not product_uuids or not es.ping():
        return {"status": "skipped", "reason": "No data or ES unavailable"}

    if not es.indices.exists(index=index_name):
        ProductDocument.init(using=es)

    actions = (
        {
            "_op_type": "index",
            "_index": index_name,
            "_id": str(product.uuid),
            "_source": ProductDocument().to_dict(product)
        }
        for product in Product.objects.filter(uuid__in=product_uuids).iterator(chunk_size=5000)
    )

    try:
        # Используем parallel_bulk для ускорения
        success, failed = 0, 0
        for ok, result in helpers.parallel_bulk(
            es,
            actions,
            chunk_size=2000,
            thread_count=4,
            request_timeout=60
        ):
            if ok:
                success += 1
            else:
                failed += 1
                logger.error(f"ES indexing failed: {result}")

        es.indices.refresh(index=index_name)
        return {
            "status": "success",
            "indexed": success,
            "failed": failed,
            "total": len(product_uuids)
        }
    except Exception as e:
        logger.critical(f"Bulk index error: {str(e)}")
        return {"status": "failed", "error": str(e)}