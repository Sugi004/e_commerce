from django.urls import path
from .productsApi import create_product,\
      delete_product, update_product, get_single_product, submit_review
from .views import render_products

urlpatterns = [
    path('', render_products, name= 'render_products'),
    path('<str:id>', get_single_product, name='get_single_product'),
    path('create/',create_product, name="create_product"),
    path('delete/<str:product_id>',delete_product, name="delete_product"),
    path('edit/<str:product_id>',update_product, name="update_product"),
    # path('api/products/', render_products , name='get_products'),
    path("<str:product_id>/submit_review/", submit_review, name="submit_review"),
]