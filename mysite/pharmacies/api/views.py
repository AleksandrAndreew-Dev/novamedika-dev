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


@api_view(['POST'])
@parser_classes([MultiPartParser])
@permission_classes([AllowAny])
def upload_csv(request, slug):
    """
    Endpoint to upload a CSV file without headers and add products to the database.
    """
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

        for row in reader:

            try:
                # Map row data to field names
                row_data = dict(zip(fieldnames, row))
                print(f"Row data: {row_data}")
                row_data['expiry_date'] = convert_date_format(row_data['expiry_date'])
                row_data['import_date'] = convert_date_format(row_data['import_date'])

                # Validate pharmacy

                pharmacy = Pharmacy.objects.get(slug=slug)
                # Create and save product
                product = Product.objects.create(
                    name=row_data['name'],
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
            except Pharmacy.DoesNotExist:
                print(f"Pharmacy not found for row: {row[:20]}")
            except Exception as e:
                print(f"Error processing row: {row[:20]}, error: {e}")

        return JsonResponse({"message": f"{created_count} products successfully added."}, status=201)

    except Exception as e:
        print(f"Error processing file: {e}")
        return JsonResponse({"error": "Failed to process the file."}, status=500)
