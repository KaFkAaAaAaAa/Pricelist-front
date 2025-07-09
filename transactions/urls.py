from django.urls import path

from . import views

# transactions/

urlpatterns = [
    path("offer-list/", views.offer_list, name="offer_list"),
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
        views.client_transaction_detail,
        name="client_transaction_detail",
    ),
    path(
        "admin/<uuid:transaction_uuid>/add-item/",
        views.add_new_item_to_transaction,
        name="add_new_item_to_transaction",
    ),
    path(
        "<uuid:transaction_uuid>/add-item/",
        views.add_new_item_to_transaction,
        name="add_new_item_to_transaction",
    ),
    path(
        "<uuid:transaction_uuid>/",
        views.admin_transaction_detail,
        name="client_transaction_detail",
    ),
    path(
        "logistics/<uuid:transaction_uuid>/",
        views.logistics_transaction_detail,
        name="logistics_transaction_detail",
    ),
    path(
        "<uuid:transaction_uuid>/change-status/",
        views.change_status,
        name="change_status",
    ),
    path(
        "<uuid:transaction_uuid>/print/",
        views.print_transaciton,
        name="print_transaciton",
    ),
    path(
        "delete/<uuid:transaction_uuid>/",
        views.delete_transaction,
        name="delete_transaction",
    ),
    path(
        "admin/<uuid:transaction_uuid>/<uuid:item_uuid>/edit/",
        views.edit_transaction_item,
        name="edit_transaction_item",
    ),
    path(
        "<uuid:transaction_uuid>/<uuid:item_uuid>/edit/",
        views.edit_transaction_item,
        name="edit_transaction_item",
    ),
    path(
        "admin/<uuid:transaction_uuid>/<uuid:item_uuid>/delete/",
        views.delete_transaction_item,
        name="delete_transaction_item",
    ),
    path(
        "<uuid:transaction_uuid>/<uuid:item_uuid>/delete/",
        views.delete_transaction_item,
        name="delete_transaction_item",
    ),
    path("", views.client_transactions, name="client_transactions"),
    path("admin/", views.admin_transactions, name="admin_transactions"),
    path("prognose/", views.prognose_list, name="prognose_list"),
    path(
        "<uuid:transaction_uuid>/<uuid:item_uuid>/add-photo/",
        views.add_photo,
        name="add_photo",
    ),
    path(
        "<uuid:transaction_uuid>/<uuid:item_uuid>/photos/<str:file>/delete",
        views.delete_photo,
        name="delete_photo",
    ),
    path(
        "<uuid:transaction_uuid>/<uuid:item_uuid>/photos/<str:file>",
        views.get_photo,
        name="get_photo",
    ),
]
