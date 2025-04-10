from django.urls import path
from . import views

urlpatterns = [
    path("", views.my_orders, name="my_orders"),
    path("track_order/<str:order_id>/", views.track_order, name="track_order"),
    path("cancel_order/<str:order_id>/", views.cancel_order, name="cancel_order"),
    path("request_refund/<str:order_id>/", views.request_refund, name="request_refund"),
]