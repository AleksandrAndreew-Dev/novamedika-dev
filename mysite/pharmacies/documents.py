# documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Product, Pharmacy


@registry.register_document
class ProductDocument(Document):
    pharmacy = fields.ObjectField(properties={
        'name': fields.TextField(),
        'pharmacy_number': fields.TextField(),
        'city': fields.KeywordField(),
    })

    price = fields.FloatField()
    quantity = fields.FloatField()
    total_price = fields.FloatField()
    wholesale_price = fields.FloatField()
    retail_price = fields.FloatField()

    class Index:
        name = 'products'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Product
        fields = [
            'name',
            'form',
            'manufacturer',
            'country',
        ]

    def to_dict(self, product):
        return {
            "name": product.name,
            "form": product.form,
            "manufacturer": product.manufacturer,
            "country": product.country,
            "price": float(product.price),
            "quantity": float(product.quantity),
            "total_price": float(product.total_price),
            "wholesale_price": float(product.wholesale_price),
            "retail_price": float(product.retail_price),
            "pharmacy": {
                "name": product.pharmacy.name if product.pharmacy else "",
                "pharmacy_number": str(product.pharmacy.pharmacy_number) if product.pharmacy else "",
                "city": product.pharmacy.city if product.pharmacy else "",
            }
        }