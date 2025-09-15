# signals.py
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import Product, Pharmacy
from .tasks import update_elasticsearch_index, update_pharmacy_city_in_index


@receiver(pre_delete, sender=Pharmacy)
def store_pharmacy_products(sender, instance, **kwargs):
    # Используем итератор для экономии памяти
    instance._product_uuids = [
        str(uuid) for uuid in 
        instance.products.values_list('uuid', flat=True).iterator(chunk_size=3000)
    ]



@receiver(post_save, sender=Product)
def update_product_in_index(sender, instance, **kwargs):    
    """Обновляет продукт в индексе при сохранении"""
    update_elasticsearch_index.delay()

@receiver(post_delete, sender=Product)
def delete_product_from_index(sender, instance, **kwargs):
    """Удаляет продукт из индекса"""
    update_elasticsearch_index.delay()

@receiver(post_save, sender=Pharmacy)
def update_pharmacy_index(sender, instance, **kwargs):
    """Обновляет индексы продуктов при изменении аптеки"""
    if 'city' in (kwargs.get('update_fields') or []) or kwargs.get('created', False):
        update_pharmacy_city_in_index.delay(instance.name, str(instance.pharmacy_number))
    else:
        update_elasticsearch_index.delay()

@receiver(post_delete, sender=Pharmacy)
def delete_pharmacy_index(sender, instance, **kwargs):
    """Удаляет продукты аптеки из индекса"""
    from .tasks import remove_products_from_index
    remove_products_from_index.delay(getattr(instance, '_product_uuids', []))

    