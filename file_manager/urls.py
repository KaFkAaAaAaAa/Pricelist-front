from django.urls import path

from . import views

urlpatterns = [
    path(
        "<uuid:transaction_uuid>/invoice/",
        views.upload_transactions_invoice,
        name="transaction_invoice",
    ),
    path(
        "<uuid:transaction_uuid>/",
        views.transaction_files,
        name="transaction_files",
    ),
]
