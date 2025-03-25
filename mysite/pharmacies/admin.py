from django.contrib import admin
from pharmacies.models import Pharmacy, Product, Order

@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ['name', 'pharmacy_number', 'city', 'address', 'phone', 'opening_hours']
    list_filter = ['name', 'pharmacy_number', 'city', 'address', 'phone', 'opening_hours']
    search_fields = ['name', 'pharmacy_number']
    list_editable = ['city', 'address', 'phone', 'opening_hours']  # Убрали 'name' из list_editable
    list_display_links = ['name', 'pharmacy_number']
    prepopulated_fields = {'slug': ('name', 'pharmacy_number')}# Добавили list_display_links

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'form', 'manufacturer', 'country', 'serial', 'price', 'quantity', 'pharmacy']
    list_filter = ['name', 'form', 'manufacturer', 'country', 'serial', 'price', 'quantity', 'pharmacy']
    search_fields = ['name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['processed', 'pharmacy_name', 'pharmacy_number',
                    'user_name', 'user_surname', 'user_phone',
                    'product_name', 'product_price', 'quantity']


