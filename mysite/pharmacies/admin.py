from django.contrib import admin
from pharmacies.models import Pharmacy, Product

@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ['name', 'pharmacy_number', 'city', 'address', 'phone', 'opening_hours']
    list_filter = ['name', 'pharmacy_number', 'city', 'address', 'phone', 'opening_hours']
    search_fields = ['name', 'pharmacy_number']
    list_editable = ['city', 'address', 'phone', 'opening_hours']  # Убрали 'name' из list_editable
    list_display_links = ['name', 'pharmacy_number']  # Добавили list_display_links

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturer', 'country', 'serial', 'price', 'quantity', 'pharmacy']
    list_filter = ['name', 'manufacturer', 'country', 'serial', 'price', 'quantity', 'pharmacy']
    search_fields = ['name']
