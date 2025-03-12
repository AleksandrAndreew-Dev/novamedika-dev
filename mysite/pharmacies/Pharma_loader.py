import csv
from datetime import datetime
from .models import Product, Pharmacy

def import_csv_to_db(csv_file_path, pharmacy_name, city, address):
    pharmacy, created = Pharmacy.objects.get_or_create(name=pharmacy_name, city=city, address=address)

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            Product.objects.create(
                name=row[0],
                manufacturer=row[1],
                country=row[2],
                serial=row[3],
                price=float(row[4]),
                quantity=float(row[5]),
                total_price=float(row[6]),
                expiry_date=datetime.strptime(row[7], '%d.%m.%Y').date(),
                category=row[8],
                import_date=datetime.strptime(row[9], '%d.%m.%Y').date(),
                internal_code=row[10],
                wholesale_price=float(row[11]),
                retail_price=float(row[12]),
                distributor=row[13],
                internal_id=row[14],
                pharmacy=pharmacy
            )

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Import products from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str)

    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']
        import_csv_to_db(csv_file_path)
        self.stdout.write(self.style.SUCCESS('Successfully imported products'))
# python manage.py import_csv_to_db mysite/pharmacies/pharma_stores/A1.csv "1"