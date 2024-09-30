from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_bag, name='view_bag'),
    path('add/<item_id>/', views.add_to_bag, name='add_to_bag'),
    path('add_custom_drone/', views.add_custom_drone_to_bag, name='add_custom_drone_to_bag'),
]