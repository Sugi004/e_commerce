from django.urls import path
from .usersApi import update_user, delete_user
from .address import add_address
from .profileView import profile_view
from .views import render_users_admin, edit_user

urlpatterns = [
    path('update/<str:user_id>', update_user, name='update_user'),
    path('edit/<str:user_id>', edit_user, name='edit_user'),
    path("delete/<str:user_id>", delete_user, name="delete_user"),
    path("<str:user_id>/address", add_address, name = "add_address"),
    path('<str:user_id>', profile_view, name='profile_view'),
    path('admin/users/', render_users_admin, name='render_users_admin'),
    path('edit/<str:user_id>/', edit_user, name='edit_user'),
]
