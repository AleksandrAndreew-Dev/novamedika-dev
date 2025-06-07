from django.urls import path

from . import views

app_name = 'pharmacies'

urlpatterns = [
    path('', views.index, name='index'),
    # Новый маршрут для стартовой страницы

    path('search/', views.search, name='search'),
    path('search_products/', views.search_products, name='search_products'),
    path('search_pharmacies/', views.search_pharmacies, name='search_pharmacies'),
    path('cookie_policy/', views.cookie_policy, name='cookie_policy'),
   
]
