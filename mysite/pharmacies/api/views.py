
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
        'СУПП', 'ГЕЛЬ', 'КАПЛИ', 'ФЛ', 'Р-Р', 'ТУБА', 'капс',  'уп', 'паста',
        'пак', 'пак.,', 'пак.', 'пор', 'пор.', 'жев.табл', 'жев.табл.', 'фильтр-пакет',
        'фильтр-пакет,', 'табл.шип', 'ТАБЛ.РАССАС', 'конт', 'крем', 'табл.жев',
        'драже', 'ф-кап', 'линим', 'капс.рект', 'фл.,', 'супп.ваг', 'саше', 'пастилки',
    ]

    if not product_string:
        return "-", "-"

    # Регулярное выражение для поиска формы (ключевое слово + остаток строки)
    form_regex = re.compile(
        r'(' + '|'.join(re.escape(kw) for kw in form_keywords) + r')([\s\.,].*)?$',
        re.IGNORECASE
    )

    match = form_regex.search(product_string)
    if match:
        form_start = match.start()
        name_part = product_string[:form_start].strip()  # Часть до формы
        form_part = product_string[form_start:].strip()  # Форма и всё после неё

        # Удаляем лишние пробелы/знаки препинания в начале формы
        form_part = re.sub(r'^[\s\.,]+', '', form_part)

        # Если name_part пусто (например, строка начинается с формы), возвращаем "-" для названия
        return (name_part if name_part else "-", form_part)

    # Если форма не найдена, возвращаем исходную строку как название, а форму как "-"
    return (product_string, "-")




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

def bulk_delete_elasticsearch(product_uuids):
    es = es_client
    index_name = ProductDocument.Index.name

    if not product_uuids or not es.ping():
        return {"status": "skipped", "reason": "No data or ES unavailable"}

    try:
        actions = [
            {
                "_op_type": "delete",
                "_index": index_name,
                "_id": str(uuid)
            }
            for uuid in product_uuids
        ]
        helpers.bulk(es, actions, chunk_size=3000, request_timeout=60)
        es.indices.refresh(index=index_name)
        return {"status": "success", "count": len(product_uuids)}
    except Exception as e:
        logger.error(f"Bulk delete error: {str(e)}")
        return {"status": "failed", "error": str(e)}

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
            # Ensure the pharmacy exists
            existing_pharmacy = Pharmacy.objects.filter(
                name=normalized_name,
                pharmacy_number=str(pharmacy_number)
            ).first()

            current_city = existing_pharmacy.city if existing_pharmacy and existing_pharmacy.city else 'New'

            # Создаём или обновляем аптеку
            pharmacy, created = Pharmacy.objects.update_or_create(
                name=normalized_name,
                pharmacy_number=str(pharmacy_number),
                defaults={'city': current_city}
            )

            # Delete all existing products for the pharmacy

            existing_products = Product.objects.filter(pharmacy=pharmacy)
            product_uuids_to_delete = list(existing_products.values_list('uuid', flat=True))
            bulk_delete_elasticsearch(product_uuids_to_delete)
            existing_products.delete()

            # Parsing CSV
            fieldnames = [
                'name', 'manufacturer', 'country', 'serial', 'price', 'quantity',
                'total_price', 'expiry_date', 'category', 'import_date',
                'internal_code', 'wholesale_price', 'retail_price',
                'distributor', 'internal_id', 'pharmacy_number'
            ]

            reader = csv.DictReader(StringIO(file_content), fieldnames=fieldnames, delimiter=';')
            created_count = 0
            errors = []
            processed_products = set()  # Track processed products to avoid duplicates

            for row in reader:
                try:
                    if not any(row.values()):
                        continue

                    # Normalize product details
                    product_name = row['name']
                    product_form = '-'
                    if row['category'] == 'Лексредства':
                        product_name, product_form = parse_product_details(row['name'])
                    serial = re.sub(r'[\s\-_]+', '', row['serial']).upper()
                    expiry_date = convert_date_format(row['expiry_date'])
                    import_date = convert_date_format(row['import_date'])

                    # Avoid processing duplicates in the CSV file
                    product_key = (product_name, serial, expiry_date)
                    if product_key in processed_products:
                        continue  # Skip duplicate entry
                    processed_products.add(product_key)

                    # Create new product entry
                    Product.objects.create(
                        pharmacy=pharmacy,
                        name=product_name,
                        form=product_form,
                        manufacturer=row['manufacturer'].strip(),
                        country=row['country'].strip(),
                        serial=serial,
                        price=float(row['price'].replace(',', '.')) if row['price'] else 0.0,
                        quantity=float(row['quantity'].replace(',', '.')) if row['quantity'] else 0.0,
                        expiry_date=expiry_date,
                        category=row['category'],
                        import_date=convert_date_format(row['import_date']),
                        internal_code=row['internal_code'],
                        wholesale_price=float(row['wholesale_price'].replace(',', '.')) if row['wholesale_price'] else None,
                        retail_price=float(row['retail_price'].replace(',', '.')) if row['retail_price'] else None,
                        distributor=row['distributor'].strip(),
                        internal_id=row['internal_id']
                    )
                    created_count += 1

                except Exception as e:
                    errors.append(f"Row error: {str(e)} | Data: {dict(row)}")
                    logger.error(f"Row error: {str(e)} | Data: {dict(row)}")
                    continue

            # Update Elasticsearch
            bulk_update_elasticsearch.delay([p.uuid for p in Product.objects.filter(pharmacy=pharmacy)])

            # Update task record status
            task_record.result = {
                "created": created_count,
                "errors": len(errors),
                "error_details": errors[:10]  # Limit stored errors
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

    # Используем Product.objects.filter для оптимизации запроса
    products = Product.objects.filter(uuid__in=product_uuids).select_related('pharmacy')

    actions = (
        {
            "_op_type": "index",  # Используем 'index' вместо 'update'
            "_index": index_name,
            "_id": str(product.uuid),
            "_source": ProductDocument().to_dict(product)  # Полный документ
        }
        for product in products
    )

    try:
        helpers.bulk(es, actions, chunk_size=3000, request_timeout=60)
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
