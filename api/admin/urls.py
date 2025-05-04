from django.urls import path
from .views import render_users_admin, \
    render_admin_panel, manage_coupons, \
    view_refund_requests, moderate_reviews, manage_categories, manage_products

urlpatterns = [

    path('', render_admin_panel, name='render_admin_panel'),
    path('users/', render_users_admin, name='render_users_admin'),
    path('coupons/', manage_coupons, name='manage_coupons'),
    path("refund_requests/", view_refund_requests, name="view_refund_requests"),
    path("reviews/", moderate_reviews, name="moderate_reviews"),
    path("categories/", manage_categories, name="manage_categories"),
    path("products/", manage_products, name="manage_products"),
]