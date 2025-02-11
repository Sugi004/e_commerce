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
from api.users.usersApi import get_users, create_user
from api.login.views import login_view, logout_view, sign_up




urlpatterns = [
    path('products/',include('api.products.urls')),
    path('users/', get_users),
    path("login/", login_view, name="login_view"),
    path('logout/', logout_view, name='logout_view'),
    path('create/', create_user, name='create_user'),
    path('signup/', sign_up, name='sign_up'),
    path('profile/', include('api.users.urls'))
]
