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

from django.conf import settings
from django.conf.urls.static import static

# from django.contrib import admin
from django.urls import path, re_path
from Pricelist import views
from admin import admin_views
from django.conf.urls.i18n import set_language


urlpatterns = (
    [
        path("profile/", views.profile, name="profile"),
        path("login/", views.login_view, name="login"),
        path("logout/", views.logout_view, name="logout"),
        path("register/", views.register_view, name="register"),
        path("profile/change-password/", views.change_password, name="change_password"),
        path("client_dashboard/", views.client_panel, name="client_dashboard"),
        path("", views.price_list, name="price_list"),
        path("item/<str:item_sku>/", views.item_detail, name="item_detail"),
        path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
        path("admin/items/", views.admin_items, name="item_list"),
        path("admin/items/<str:item_sku>/edit", views.edit_item, name="edit_item"),
        path(
            "admin/items/<str:item_sku>/delete", views.delete_item, name="delete_item"
        ),
        path("admin/items/add", views.add_item, name="add_item"),
        path(
            "admin/items/<str:item_sku>/upload-image/",
            views.upload_image,
            name="upload_image",
        ),
        # using /pictures/{img_path} works around url input from views and paths in fs where pictures is the root
        # urls should always look like delete/
        path(
            "admin/items/delete/images/<str:image_path>",
            views.delete_image,
            name="delete_image",
        ),
        path(
            "admin/items/<str:item_sku>/images/",
            views.admin_images,
            name="admin_images",
        ),
        path("admin/items/delete", views.null_delete, name="null_delete"),
        path("admin/new-admin/", views.new_admin, name="new_admin"),
        path("admin/new-clients/", views.new_users, name="new_users"),
        path(
            "admin/clients/<uuid:user_id>/assign-admin",
            views.assign_admin,
            name="assign_admin",
        ),
        path(
            "admin/my-users/",
            views.my_users,
            name="my_users",
        ),
        path(
            "admin/clients/<uuid:user_id>/activate-user/",
            views.activate_user,
            name="activate_user",
        ),
        path("admin/clients/", views.client_list, name="client_list"),
        path("admin/clients/add/", views.client_add, name="client_add"),
        path(
            "admin/clients/<uuid:client_id>", views.client_detail, name="client_detail"
        ),
        path(
            "admin/clients/<uuid:client_id>/edit",
            views.edit_client,
            name="edit_client",
        ),
        path(
            "admin/clients/<uuid:client_id>/delete",
            views.client_delete,
            name="client_delete",
        ),
        path("change-password/", views.change_password, name="change_password"),
        path("admin/admins/", admin_views.admin_list, name="admin_list"),
        path(
            "admin/admins/<uuid:admin_id>/delete/",
            admin_views.delete_admin,
            name="delete_admin",
        ),
        path(
            "admin/admins/<uuid:admin_id>/edit/",
            admin_views.edit_admin,
            name="edit_admin",
        ),
        path("set_language/", set_language, name="set_language"),
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
)
