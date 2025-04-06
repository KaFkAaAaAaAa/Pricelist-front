from django.urls import path

from . import views

urlpatterns = [
    # path(
    #     "<uuid:transaction_uuid>/invoice/",
    #     views.upload_transactions_invoice,
    #     name="transaction_invoice",
    # ),
    # path(
    #     "<uuid:transaction_uuid>/",
    #     views.transaction_files,
    #     name="transaction_files",
    # ),
    path(
        "<uuid:transaction_uuid>/",
        views.browse_transaction_dir,
        name="browse_transaction_root",
    ),
    path(
        "<uuid:transaction_uuid>/<str:directory_name>/",
        views.browse_transaction_dir,
        name="browse_transaction_folder",
    ),
    path(
        "<uuid:transaction_uuid>/<str:directory_name>/file/<str:file_name>",
        views.file_interaction,
        name="directory_file",
    ),
    path(
        "<uuid:transaction_uuid>/file/<str:file_name>",
        views.file_interaction,
        name="file",
    ),
]
