from django.urls import path

from . import views

app_name = 'pharmacies'

urlpatterns = [
    path('', views.index, name='index'),
    # Новый маршрут для стартовой страницы
    path('pharmacies/', views.pharmacy_list, name='pharmacy_list'),
    path('<str:pharmacy_name>/<str:pharmacy_number>/', views.pharmacy_detail, name='pharmacy_detail'),
    path('search/', views.search, name='search'),
    path('search_products/', views.search_products, name='search_products'),
    path('search_pharmacies/', views.search_pharmacies, name='search_pharmacies'),
    path('reserve/', views.reserve, name='reserve'),
]
