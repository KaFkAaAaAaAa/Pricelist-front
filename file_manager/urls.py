from django.urls import path

from . import views

urlpatterns = [
    path(
        "<uuid: transaction_uuid>",
        views.upload_transactions_invoice,
        "upload_transaction",
    ),
]
