from django.urls import path

from . import views

app_name = 'subjects'

urlpatterns = [
    path('check_status/<str:task_id>/', views.check_processing_status, name='check_status'),
    path('<str:pharmacy_name>/<int:pharmacy_number>/', views.upload_csv, name='upload_csv'),
]
