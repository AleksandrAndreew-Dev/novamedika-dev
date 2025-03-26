import csv

import chardet
from django.http import JsonResponse
from pharmacies.api.serializers import ProductSerializer
from pharmacies.models import Product, Pharmacy
from rest_framework import generics
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()[:20]

    serializer_class = ProductSerializer


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


from datetime import datetime


def convert_date_format(date_string):
    """
    Convert DD.MM.YYYY format to YYYY-MM-DD format.
    """
    try:
        return datetime.strptime(date_string, '%d.%m.%Y').strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}")


import re
def parse_product_details(product_string):
    # Ключевые слова для лекарственных средств


    # Базовые ключевые слова для формы
    form_keywords = [
        'АМП', 'ТАБЛ', 'ТАБЛ.', 'ТАБЛ,', 'ТАБЛ', 'ТАБЛ.П/О', 'ТАБЛ.РАСТВ.', 'МАЗЬ',
        'СУПП', 'ГЕЛЬ', 'КАПЛИ', 'ФЛ', 'Р-Р', 'ТУБА', 'капс',
        'уп', 'паста', 'пак', 'пак.,', 'пак.', 'пор', 'пор.', 'жев.табл', 'жев.табл.',
        'фильтр-пакет', 'фильтр-пакет,', 'табл.шип', 'ТАБЛ.РАССАС',
        'конт', 'крем', 'табл.жев', 'драже', 'ф-кап', 'крем', 'линим',
        'капс.рект', 'фл.,', 'супп.ваг',  'саше', 'пастилки',
    ]

    # Проверить, начинается ли строка с ключевого слова формы
    first_word = product_string.split()[0]
    if first_word.strip().upper() in {keyword.upper() for keyword in form_keywords}:
        # Вернуть строку без изменений, если она начинается с ключевого слова формы
        return product_string, "-"

    # Скомпилировать регулярное выражение для формы
    form_regex = re.compile(
        r'^(' + '|'.join(re.escape(keyword) for keyword in form_keywords) + r')[\s\.,]*$', re.IGNORECASE
    )

    parts = product_string.split()
    name_parts = []
    form_parts = []
    is_form = False

    for part in parts:
        # Проверка, соответствует ли текущая часть ключевым словам формы
        if form_regex.match(part) or is_form:
            is_form = True
            form_parts.append(part)
        else:
            name_parts.append(part)

    # Если вся строка является названием
    name = " ".join(name_parts).strip()
    form = " ".join(form_parts).strip()
    return name, form

@api_view(['POST'])
@parser_classes([MultiPartParser])
@permission_classes([AllowAny])
def upload_csv(request, pharmacy_name, pharmacy_number):
    """
    Endpoint to upload a CSV file without headers and update products in the database.
    Old records for the same pharmacy will be removed, and new ones will be added.
    """
    valid_pharmacies_names = {
        'novamedika': 'Новамедика',
        'ekliniya': 'Эклиния'
    }
    normalized_pharmacy_name = valid_pharmacies_names.get(pharmacy_name)
    if not normalized_pharmacy_name:
        return JsonResponse({'error': 'Invalid pharmacy_name provided'}, status=400)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "CSV file is required."}, status=400)

    try:
        # Decode the file
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        decoded_file = raw_data.decode(encoding).splitlines()

        # Define field names manually since the CSV has no headers
        fieldnames = [
            'name', 'manufacturer', 'country', 'serial', 'price', 'quantity',
            'total_price', 'expiry_date', 'category', 'import_date',
            'internal_code', 'wholesale_price', 'retail_price',
            'distributor', 'internal_id', 'pharmacy_number'
        ]

        # Use csv.reader instead of csv.DictReader, then map manually
        reader = csv.reader(decoded_file, delimiter=';')
        created_count = 0

        # Remove old products for the specified pharmacy
        pharmacy = Pharmacy.objects.filter(name=normalized_pharmacy_name, pharmacy_number=pharmacy_number).first()
        if pharmacy:
            Product.objects.filter(pharmacy=pharmacy).delete()

        # Create or update pharmacy
        pharmacy, created = Pharmacy.objects.get_or_create(
            name=normalized_pharmacy_name, pharmacy_number=pharmacy_number
        )

        for row in reader:
            try:
                # Map row data to field names
                row_data = dict(zip(fieldnames, row))

                # Convert date formats
                row_data['expiry_date'] = convert_date_format(row_data['expiry_date'])
                row_data['import_date'] = convert_date_format(row_data['import_date'])

                # Parse product details
                name, form = parse_product_details(row_data['name'])

                # Create and save product
                product = Product.objects.create(
                    name=name,
                    form=form,
                    manufacturer=row_data['manufacturer'],
                    country=row_data['country'],
                    serial=row_data['serial'],
                    price=row_data['price'],
                    quantity=row_data['quantity'],
                    total_price=row_data['total_price'],
                    expiry_date=row_data['expiry_date'],
                    category=row_data['category'],
                    import_date=row_data['import_date'],
                    internal_code=row_data['internal_code'],
                    wholesale_price=row_data['wholesale_price'],
                    retail_price=row_data['retail_price'],
                    distributor=row_data['distributor'],
                    internal_id=row_data['internal_id'],
                    pharmacy=pharmacy
                )

                product.save()
                created_count += 1

            except Exception as e:
                print(f"Error processing row: {row[:20]}, error: {e}")

        return JsonResponse({"message": f"{created_count} products successfully added after resetting the old ones."}, status=201)

    except Exception as e:
        print(f"Error processing file: {e}")
        return JsonResponse({"error": "Failed to process the file."}, status=500)

