from django.urls import path

from . import views

app_name = 'subjects'

urlpatterns = [
    path('<str:pharmacy_name>/<int:pharmacy_number>/', views.upload_csv, name='upload_csv'),
]
