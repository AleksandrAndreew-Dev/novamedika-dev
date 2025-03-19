from django.urls import path
from . import views

app_name = 'subjects'

urlpatterns = [
    path('subjects/', views.ProductListView.as_view(), name='subject_list'),
    path('subjects/<pk>/', views.ProductDetailView.as_view(), name='subject_detail'),
    path('upload-csv/<slug:slug>/', views.upload_csv, name='upload_csv'),
]