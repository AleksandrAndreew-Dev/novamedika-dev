from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry

from .models import Product


@registry.register_document
class ProductDocument(Document):
    class Index:
        # Указываем имя индекса в Elasticsearch
        name = 'products'

    class Django:
        # Привязываем документ к модели Product
        model = Product

        # Указываем поля модели, которые попадут в Elasticsearch
        fields = [
            'name',

        ]
