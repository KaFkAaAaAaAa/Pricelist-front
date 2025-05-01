from . import views
from django.urls import path


urlpatterns = (
    # prefix: admin/items/
    [
        path("", views.admin_items, name="item_list"),
        path("<str:item_sku>/edit", views.edit_item, name="edit_item"),
        path(
            "<str:item_sku>/delete", views.delete_item, name="delete_item"
        ),
        path("add", views.add_item, name="add_item"),
        path(
            "<str:item_sku>/upload-image/",
            views.upload_image,
            name="upload_image",
        ),
        # using /images/{img_path} works around url input from views and paths in fs where pictures is the root
        # urls should always look like delete/
        path(
            "delete/images/<str:image_path>",
            views.delete_image,
            name="delete_image",
        ),
        path(
            "<str:item_sku>/images/",
            views.admin_images,
            name="admin_images",
        ),
        path("delete/", views.null_delete, name="null_delete"),
    ]
)
