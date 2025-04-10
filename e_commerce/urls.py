"""
URL configuration for e_commerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.shortcuts import redirect
from api.users.usersApi import create_user
from api.login.views import login_view, logout_view, sign_up, password_reset





urlpatterns = [
    path("", lambda request: redirect('render_products'), name='root'),
    path('products/',include('api.products.urls')),
    path("login/", login_view, name="login_view"),
    path('logout/', logout_view, name='logout_view'),
    path('password-reset/<str:reset_token>/', password_reset, name='password_reset'),
    path('create/', create_user, name='create_user'),
    path('signup/', sign_up, name='sign_up'),
    path('profile/', include('api.users.urls')),
    path('cart/', include('api.cart_management.urls')),
    path('checkout/', include('api.checkout.urls')),
    path('orders/', include('api.orders.urls')),
]
