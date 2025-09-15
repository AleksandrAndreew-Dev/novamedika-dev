from django.contrib import admin
from pharmacies.models import Pharmacy, Product

@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'pharmacy_number', 'city',
        'address', 'phone', 'opening_hours'
    ]
    list_filter = [
        'name', 'pharmacy_number', 'city',
        'address', 'phone', 'opening_hours'
    ]
    search_fields = ['name', 'pharmacy_number']
    list_editable = ['city', 'address', 'phone', 'opening_hours']
    list_display_links = ['name', 'pharmacy_number']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .tasks import update_pharmacy_city_in_index
        update_pharmacy_city_in_index.delay(
            obj.name, str(obj.pharmacy_number)
        )

    def delete_model(self, request, obj):
        product_uuids = list(
        obj.products.values_list('uuid', flat=True).iterator(chunk_size=2000)
        )
        super().delete_model(request, obj)
        from .tasks import remove_products_from_index
        remove_products_from_index.delay(product_uuids)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'form', 'manufacturer', 'country',
        'serial', 'price', 'quantity', 'pharmacy'
    ]
    list_filter = [
        'name', 'form', 'manufacturer', 'country',
        'serial', 'price', 'quantity', 'pharmacy'
    ]
    search_fields = ['name']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .tasks import update_elasticsearch_index
        update_elasticsearch_index.delay()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        from .tasks import update_elasticsearch_index
        update_elasticsearch_index.delay()
