from django.urls import path
from . import views

urlpatterns = [
    path('', views.all_products, name='products'),
    path('<product_id>', views.product_detail, name='product_detail'),
    path('customize/', views.custom_product, name='custom_product'),
    path('add/', views.add_product, name='add_product'),
    path('edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('customize/edit/<int:product_id>/', views.edit_custom_product, name='edit_custom_product'),
    path('customize/delete/<int:product_id>/', views.delete_custom_product, name='delete_custom_product'),
    path('compare/<int:product_id>/', views.compare_products, name='compare_product'),

]