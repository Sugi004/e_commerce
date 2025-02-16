from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_cart, name='view_cart'),
    path('update/<str:product_id>', views.update_cart, name='update_cart'),
    path('remove/<str:product_id>', views.remove_from_cart, name='remove_from_cart'),
    # path('checkout/', views.checkout, name='checkout'),
    path('add/<str:product_id>', views.add_to_cart, name='add_to_cart'),
    path('delete/<str:product_id>', views.delete_cart_view, name='remove_from_cart'),
    path('clear/', views.clear_cart_view, name='clear_cart'),

]