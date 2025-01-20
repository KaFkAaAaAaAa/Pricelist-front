"""
URL configuration for Pricelist project.

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
# from django.contrib import admin
from django.urls import path
from Pricelist import views


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('', views.price_list, name='price_list'),
    path('<str:item_sku>/', views.item_detail, name='item_detail'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/items/', views.admin_items, name='item_list'),
    path('admin/items/<str:item_sku>/edit', views.edit_item, name='edit_item'),
    path('admin/items/<str:item_sku>/delete', views.delete_item, name='delete_item'),
    path('admin/items/add', views.add_item, name='add_item'),
]
