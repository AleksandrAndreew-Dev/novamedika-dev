from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Product, Pharmacy

@registry.register_document
class ProductDocument(Document):
    pharmacy = fields.ObjectField(properties={
        'name': fields.TextField(),
        'city': fields.TextField(),
        'address': fields.TextField(),
        'phone': fields.TextField(),
    })

    class Index:
        name = 'products'  # Name of the Elasticsearch index

    class Django:
        model = Product  # Model associated with this Document
        fields = [
            'name',
            'form',
            'manufacturer',
            'price',
            'quantity',
        ]

