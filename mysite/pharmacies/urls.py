from django.urls import path
from . import views

app_name = 'pharmacies'

urlpatterns = [
    path('', views.index, name='index'),
    # Новый маршрут для стартовой страницы
    path('pharmacies/', views.pharmacy_list, name='pharmacy_list'),
    path('<str:pharmacy_name>/<str:pharmacy_number>/', views.pharmacy_detail, name='pharmacy_detail'),
    path('search/', views.product_search_with_results, name='product_search_with_results'),
    path('reserve/', views.reserve, name='reserve'),
]