from django.urls import path

from . import views

# transactions/

urlpatterns = [
    path("offer/", views.offer, name="offer"),
    path(
        "offer/<str:item_sku>/delete/",
        views.delete_from_offer,
        name="delete_from_offer",
    ),
    path(
        "offer/<str:item_sku>/edit/",
        views.edit_item_offer,
        name="edit_item_offer",
    ),
    path(
        "admin/client/<uuid:user_id>/",
        views.admin_client_transactions,
        name="client_transactions",
    ),
    path(
        "admin/<uuid:transaction_uuid>/",
        views.admin_transaction_detail,
        name="admin_transaction_detail",
    ),
    path(
        "<uuid:transaction_uuid>/",
        views.admin_transaction_detail,
        name="client_transaction_detail",
    ),
]
