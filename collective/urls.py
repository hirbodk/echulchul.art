from django.urls import path
from . import views

urlpatterns = [
    path('c/<slug:slug>/', views.collection_detail, name='collection'),
]
