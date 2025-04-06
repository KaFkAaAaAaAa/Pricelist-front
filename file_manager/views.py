import os

from django.contrib import messages
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from Pricelist.settings import (
    ADMIN_GROUPS,
    API_BASE_URL,
    CLIENT_GROUPS,
    MAX_FILE_SIZE,
    TRANSACTION_ROOT,
)
from Pricelist.utils import _get_headers, _is_admin, _make_api_request, require_auth

fs = FileSystemStorage(location=TRANSACTION_ROOT)


def _sanitize_path(path):
    """Sanitize a path against directory traversal attacks."""
    path = os.path.normpath(os.path.join(fs.base_location, path))
    if not path.startswith(fs.base_location):
        raise ValueError("Invalid file path detected!")
    return path


def _list_transaction_dir(transaction_uuid):
    if transaction_uuid not in fs.listdir("/")[0]:
        return False, False
    return fs.listdir(os.path.normpath(transaction_uuid))


def _get_file_from_transaction(transaction_uuid, file_name):
    path = _sanitize_path(os.path.join(transaction_uuid, file_name))
    file_list = _list_transaction_dir(transaction_uuid)
    if not file_list:
        return False
    if file_name in file_list[0]:
        return fs.listdir(path)
    if file_name in file_list[1]:
        with fs.open(path) as f:
            return f.read()
    return False


def _put_file_from_transaction(
    transaction_uuid, file_name, file_content, overwrite=False, path=""
):
    file_path = transaction_uuid + path
    transaction_path = os.path.join(fs.base_location, file_path)
    if not os.path.exists(transaction_path):
        os.makedirs(transaction_path, exist_ok=True)

    path = _sanitize_path(os.path.join(transaction_uuid, file_name))

    if fs.exists(path):
        if not overwrite:
            return False
        fs.delete(path)

    file_content = File(file_content)
    if file_content.size > MAX_FILE_SIZE:
        return False

    return fs.save(path, file_content)


@require_auth
def upload_transactions_invoice(request, transaction_uuid):

    # TODO: who can do that?

    if request.method == "POST" and request.FILES["file"]:
        uploaded_file = request.FILES["file"]
        _put_file_from_transaction(
            transaction_uuid,
            uploaded_file.name,
            uploaded_file.content,
            path="/invoice/",
        )
        messages.success(request, _("File upoaded successfully"))
        return render(
            request,
            "upload_success.html",
            {
                "transaction_uuid": transaction_uuid,
                "file_name": uploaded_file.name,
            },
        )
    return render(
        request,
        "upload_file.html",
        {
            "transaction_uuid": transaction_uuid,
        },
    )


@require_auth
def transaction_files(request, transaction_uuid):
    admin_url = "admin/" if _is_admin(request) else ""

    if request.session["group"] in (CLIENT_GROUPS + ADMIN_GROUPS):
        _, error = _make_api_request(
            f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}",
            headers=_get_headers(request),
        )
        if error:  # check if valid id, and if user can read that transaciton data
            return error
    dir_list, file_list = _list_transaction_dir(transaction_uuid)
    return render(
        request,
        "transaction_files.html",
        {
            "dir_list": dir_list,
            "file_list": file_list,
            "transaction_uuid": transaction_uuid,
        },
    )
