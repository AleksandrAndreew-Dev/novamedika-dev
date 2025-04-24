import csv
import re
import logging
from datetime import datetime
from io import StringIO

import chardet
from celery import shared_task
from django.db import transaction
from django.http import JsonResponse
from elasticsearch import helpers
from django.core.files.storage import default_storage
from rest_framework import generics
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny

from pharmacies.api.serializers import ProductSerializer
from pharmacies.documents import ProductDocument
from pharmacies.models import Product, Pharmacy, CsvProcessingTask
from pharmacies.tasks import remove_products_from_index, es_client, update_pharmacy_city_in_index

logger = logging.getLogger(__name__)


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()[:20]
    serializer_class = ProductSerializer


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


def convert_date_format(date_string):
    try:
        return datetime.strptime(date_string, '%d.%m.%Y').strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}")


def parse_product_details(product_string):
    form_keywords = [
        'АМП', 'ТАБЛ', 'ТАБЛ.', 'ТАБЛ,', 'ТАБЛ', 'ТАБЛ.П/О', 'ТАБЛ.РАСТВ.', 'МАЗЬ',
        'СУПП', 'ГЕЛЬ', 'КАПЛИ', 'ФЛ', 'Р-Р', 'ТУБА', 'капс', 'уп', 'паста',
        'пак', 'пак.,', 'пак.', 'пор', 'пор.', 'жев.табл', 'жев.табл.', 'фильтр-пакет',
        'фильтр-пакет,', 'табл.шип', 'ТАБЛ.РАССАС', 'конт', 'крем', 'табл.жев',
        'драже', 'ф-кап', 'линим', 'капс.рект', 'фл.,', 'супп.ваг', 'саше', 'пастилки',
    ]

    first_word = product_string.split()[0] if product_string else ''
    if first_word.strip().upper() in {kw.upper() for kw in form_keywords}:
        return product_string, "-"

    form_regex = re.compile(
        r'^(' + '|'.join(re.escape(kw) for kw in form_keywords) + r')[\s\.,]*$',
        re.IGNORECASE
    )

    parts = product_string.split() if product_string else []
    name_parts, form_parts = [], []
    is_form = False

    for part in parts:
        if form_regex.match(part) or is_form:
            is_form = True
            form_parts.append(part)
        else:
            name_parts.append(part)

    return ' '.join(name_parts).strip(), ' '.join(form_parts).strip()


@api_view(['POST'])
@parser_classes([MultiPartParser])
@permission_classes([AllowAny])
def upload_csv(request, pharmacy_name, pharmacy_number):
    try:
        if 'file' not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        file = request.FILES['file']
        if not file.name.lower().endswith('.csv'):
            return JsonResponse({"error": "Only CSV files allowed"}, status=400)

        raw_content = file.read()
        encoding = chardet.detect(raw_content)['encoding'] or 'utf-8'

        task = process_csv_task.delay(
            file_content=raw_content.decode(encoding),
            pharmacy_name=pharmacy_name,
            pharmacy_number=pharmacy_number
        )

        return JsonResponse({
            "message": "File processing started",
            "task_id": task.id,
            "status": "processing"
        }, status=202)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@shared_task(bind=True, max_retries=3, soft_time_limit=3600)
def process_csv_task(self, file_content, pharmacy_name, pharmacy_number):
    task_record = CsvProcessingTask.objects.create(
        task_id=self.request.id,
        pharmacy_name=pharmacy_name,
        pharmacy_number=pharmacy_number,
        status='processing'
    )

    try:
        pharmacy_map = {
            'novamedika': 'Новамедика',
            'ekliniya': 'Эклиния'
        }
        normalized_name = pharmacy_map.get(pharmacy_name.lower())
        if not normalized_name:
            raise ValueError(f"Invalid pharmacy: {pharmacy_name}")

        with transaction.atomic():
            # Создание/обновление аптеки
            pharmacy, created = Pharmacy.objects.update_or_create(
                name=normalized_name,
                pharmacy_number=str(pharmacy_number),
                defaults={'city': None}
            )

            # Удаление старых продуктов
            if not created:
                old_uuids = list(Product.objects.filter(
                    pharmacy=pharmacy
                ).values_list('uuid', flat=True))

                Product.objects.filter(pharmacy=pharmacy).delete()
                if old_uuids:
                    remove_products_from_index.delay(old_uuids)

            # Парсинг CSV
            fieldnames = [
                'name', 'manufacturer', 'country', 'serial', 'price', 'quantity',
                'total_price', 'expiry_date', 'category', 'import_date',
                'internal_code', 'wholesale_price', 'retail_price',
                'distributor', 'internal_id', 'pharmacy_number'
            ]

            reader = csv.DictReader(
                StringIO(file_content),
                fieldnames=fieldnames,
                delimiter=';'
            )

            batch_size = 5000
            products_batch = []
            all_uuids = []
            row_counter = 0

            for row in reader:
                try:
                    # Пропуск пустых строк
                    if not any(row.values()):
                        continue

                    # Обработка категории
                    product_form = '-'
                    if row['category'] == 'Лексредства':
                        _, product_form = parse_product_details(row['name'])

                    # Конвертация дат
                    expiry_date = convert_date_format(row['expiry_date'])
                    import_date = convert_date_format(row['import_date'])

                    # Создание продукта
                    product = Product(
                        name=row['name'],
                        form=product_form,
                        manufacturer=row['manufacturer'],
                        country=row['country'],
                        serial=row['serial'],
                        price=float(row['price'].replace(',', '.') if row['price'] else 0.0),
                        quantity=float(row['quantity'].replace(',', '.') if row['quantity'] else 0.0),
                        total_price=float(row['total_price'].replace(',', '.') if row['total_price'] else 0.0),
                        expiry_date=expiry_date,
                        category=row['category'],
                        import_date=import_date,
                        internal_code=row['internal_code'],
                        wholesale_price=float(row['wholesale_price'].replace(',', '.') if row['wholesale_price'] else 0.0),
                        retail_price=float(row['retail_price'].replace(',', '.') if row['retail_price'] else 0.0),
                        distributor=row['distributor'],
                        internal_id=row['internal_id'],
                        pharmacy=pharmacy
                    )
                    products_batch.append(product)
                    row_counter += 1

                    # Пакетное сохранение
                    if len(products_batch) >= batch_size:
                        created_products = Product.objects.bulk_create(products_batch)
                        all_uuids.extend(str(p.uuid) for p in created_products)
                        products_batch = []
                        task_record.result = {"progress": f"{row_counter} rows processed"}
                        task_record.save()

                except Exception as e:
                    logger.error(f"Row {row_counter} error: {str(e)} | Row data: {dict(row)}")
                    continue

            # Сохранение последнего пакета
            if products_batch:
                created_products = Product.objects.bulk_create(products_batch)
                all_uuids.extend(str(p.uuid) for p in created_products)

            # Обновление Elasticsearch
            if all_uuids:
                bulk_update_elasticsearch.delay(all_uuids)

            transaction.on_commit(
                lambda: update_pharmacy_city_in_index.delay(
                    normalized_name,
                    str(pharmacy_number)
                )
            )

            # Обновление статуса задачи
            task_record.result = {
                "processed_rows": row_counter,
                "products_added": len(all_uuids),
                "pharmacy": pharmacy_name,
                "pharmacy_number": pharmacy_number
            }
            task_record.status = 'completed'
            task_record.save()

        return task_record.result

    except Exception as e:
        task_record.status = 'failed'
        task_record.result = {'error': str(e)}
        task_record.save()
        logger.critical(f"Task failed: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


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
        for product in Product.objects.filter(uuid__in=product_uuids).iterator(chunk_size=2000)
    )

    try:
        helpers.bulk(es, actions, chunk_size=1000, request_timeout=60)
        es.indices.refresh(index=index_name)
        return {"status": "success", "count": len(product_uuids)}
    except Exception as e:
        logger.error(f"Bulk index error: {str(e)}")
        return {"status": "failed", "error": str(e)}


@api_view(['GET'])
@permission_classes([AllowAny])
def check_processing_status(request, task_id):
    try:
        task = CsvProcessingTask.objects.get(task_id=task_id)
        return JsonResponse({
            'status': task.status,
            'result': task.result,
            'created_at': task.created_at,
            'updated_at': task.updated_at
        })
    except CsvProcessingTask.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
