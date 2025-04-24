from django.core.management.base import BaseCommand
from pharmacies.models import Product
from pharmacies.documents import ProductDocument

from django.core.management.base import BaseCommand
from elasticsearch.helpers import bulk
from pharmacies.documents import ProductDocument
from pharmacies.models import Product

class Command(BaseCommand):
    help = "Rebuild Elasticsearch index by batching data"

    def handle(self, *args, **kwargs):
        chunk_size = 1000  # Размер батча для обработки
        products = Product.objects.all()

        for i in range(0, len(products), chunk_size):
            chunk = products[i:i + chunk_size]
            ProductDocument().update(chunk)

        self.stdout.write(self.style.SUCCESS('Successfully rebuilt index'))

