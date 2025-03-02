from django.conf import settings
from django.conf.urls.i18n import set_language
from django.conf.urls.static import static

from django.urls import include, path

from admin import admin_views
from items import views as items_views
from Pricelist import views

urlpatterns = (
    [
        path("admin/items/", include("items.urls")),
        path("transactions/", include("transactions.urls")),
        path("pdf/", include("pdfgenerator.urls")),
        path("profile/", views.profile, name="profile"),
        path("login/", views.login_view, name="login"),
        path("logout/", views.logout_view, name="logout"),
        path("register/", views.register_view, name="register"),
        path("profile/change-password/", views.change_password, name="change_password"),
        path("client_dashboard/", views.client_panel, name="client_dashboard"),
        path("", items_views.price_list, name="price_list"),
        path("item/<str:item_sku>/", items_views.item_detail, name="item_detail"),
        path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
