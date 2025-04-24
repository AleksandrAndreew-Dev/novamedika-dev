from django.db import models
from django.urls import reverse
import uuid









class Pharmacy(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, blank=True, null=True)
    pharmacy_number = models.CharField(max_length=100, blank=True, null=True)  # Код аптеки
    city = models.CharField(max_length=30, blank=True, null=True)  # Эти поля можно заполнить позже
    address = models.CharField(max_length=255, blank=True, null=True)  # Эти поля можно заполнить позже
    phone = models.CharField(max_length=20, blank=True, null=True)  # Эти поля можно заполнить позже
    opening_hours = models.CharField(max_length=255, blank=True, null=True)  # Эти поля можно заполнить позже


    def __str__(self):
        return f"{self.name} №{self.pharmacy_number}"

    def get_absolute_url(self):
        return reverse('pharmacies:pharmacy_detail', args=[self.name, self.pharmacy_number])



    class Meta:

        verbose_name = 'Pharmacy'
        verbose_name_plural = 'Pharmacies'


class Product(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    form = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    serial = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()
    category = models.CharField(max_length=255)
    import_date = models.DateField()
    internal_code = models.CharField(max_length=255)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    distributor = models.CharField(max_length=255)
    internal_id = models.CharField(max_length=255)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='products')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        serials = self.serial.split(',')
        first_serial = serials[0]
        additional_serials = ' и другие' if len(serials) > 1 else ''
        return f"{self.name} - Серийный номер: {first_serial}{additional_serials}"

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'


class Order(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_name = models.CharField(max_length=100)
    user_surname = models.CharField(max_length=100)
    user_phone = models.CharField(max_length=100)
    quantity = models.IntegerField()
    product_name = models.CharField(max_length=100)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    pharmacy_name = models.CharField(max_length=100)
    pharmacy_number = models.IntegerField()
    processed = models.BooleanField(default=False)

    def __str__(self):
        return (f"{self.pharmacy_name} {self.pharmacy_number}"
                f"{self.user_name} {self.user_surname}"
                f"{self.product_name} {self.product_price} {self.quantity}")




class CsvProcessingTask(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=255, unique=True)
    pharmacy_name = models.CharField(max_length=100)
    pharmacy_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'pharmacies_csvprocessingtask'
