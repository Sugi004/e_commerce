from django.urls import path
from .usersApi import get_user_by_id, update_user, delete_user
from .address import add_address
from .profileView import profile_view

urlpatterns = [
    path("<str:user_id>/", get_user_by_id, name="get_user_by_id"),
    path("update/<str:user_id>/", update_user, name="update_user"),
    path("delete/<str:user_id>/", delete_user, name="delete_user"),
    path("<str:user_id>/address", add_address, name = "add_address"),
    path('<str:user_id>', profile_view, name='profile'),
]
