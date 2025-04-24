# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Pharmacy
from .tasks import update_elasticsearch_index, update_pharmacy_city_in_index, remove_pharmacy_products_from_index

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
    remove_pharmacy_products_from_index.delay(str(instance.uuid))  # Используем id вместо uuid