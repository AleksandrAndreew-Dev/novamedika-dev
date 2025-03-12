# myapp/management/commands/import_csv_to_db.py

from django.core.management.base import BaseCommand
from pharmacies.models import Pharmacy, Product
import csv
from datetime import datetime

def import_csv_to_db(csv_file_path, pharmacy_number):
    pharmacy, created = Pharmacy.objects.get_or_create(pharmacy_number=pharmacy_number)

    with open(csv_file_path, newline='', encoding='cp1251') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            # Проверка и обработка данных перед созданием объекта product
            name = row[0] if row[0] else "Нет данных"
            manufacturer = row[1] if row[1] else "Нет данных"
            country = row[2] if row[2] else "Нет данных"
            serial = row[3] if row[3] else "Нет данных"
            price = float(row[4]) if row[4] else 0.0
            quantity = float(row[5]) if row[5] else 0.0
            total_price = float(row[6]) if row[6] else 0.0
            expiry_date = datetime.strptime(row[7], '%d.%m.%Y').date() if row[7] else datetime.strptime('01.01.2100', '%d.%m.%Y').date()
            category = row[8] if row[8] else "Нет данных"
            import_date = datetime.strptime(row[9], '%d.%m.%Y').date() if row[9] else datetime.now().date()
            internal_code = row[10] if row[10] else "Нет данных"
            wholesale_price = float(row[11]) if row[11] else 0.0
            retail_price = float(row[12]) if row[12] else 0.0
            distributor = row[13] if row[13] else "Нет данных"
            internal_id = row[14] if row[14] else "Нет данных"

            Product.objects.create(
                name=name,
                manufacturer=manufacturer,
                country=country,
                serial=serial,
                price=price,
                quantity=quantity,
                total_price=total_price,
                expiry_date=expiry_date,
                category=category,
                import_date=import_date,
                internal_code=internal_code,
                wholesale_price=wholesale_price,
                retail_price=retail_price,
                distributor=distributor,
                internal_id=internal_id,
                pharmacy=pharmacy
            )

class Command(BaseCommand):
    help = 'Import products from CSV file with pharmacies information'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str)
        parser.add_argument('pharmacy_number', type=str)

    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']
        pharmacy_number = options['pharmacy_number']
        import_csv_to_db(csv_file_path, pharmacy_number)
        self.stdout.write(self.style.SUCCESS('Successfully imported products with pharmacies information'))

# python manage.py import_csv_to_db pharmacies/pharma_stores/A1.csv 1
