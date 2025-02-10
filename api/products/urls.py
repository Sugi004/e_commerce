from django.urls import path
from . import views
from .productsApi import create_product, delete_product, update_product, get_products, get_single_product

urlpatterns = [
    path('', views.render_products, name= 'render_products'),
    path('<str:id>', get_single_product, name='get_single_product'),
    path('create/',create_product, name="create_product"),
    path('delete/<str:product_id>',delete_product, name="delete_product"),
    path('edit/<str:product_id>',update_product, name="update_product"),
    path('api/products/', get_products, name='get_products'),
]