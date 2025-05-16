import logging
import os

import requests
from django.contrib import messages
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseNotFound
from django.http.response import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls.exceptions import Http404
from django.utils.translation import gettext_lazy as _

from file_manager.rules import is_readable, is_writable
from Pricelist.settings import (
    ADMIN_GROUPS,
    API_BASE_URL,
    CLIENT_GROUPS,
    MAX_FILE_SIZE,
    SUPPORT_GROUPS,
    TRANSACTION_ROOT,
)
from Pricelist.utils import (
    _get_headers,
    _is_admin,
    _is_support,
    _make_api_request,
    require_auth,
)

logger = logging.getLogger(__name__)
fs = FileSystemStorage(location=TRANSACTION_ROOT)
# TODO: move to env
DIRECTORIES = ["finance", "transport"]


def _sanitize_path(path):
    """Sanitize a path against directory traversal attacks."""
    path = os.path.normpath(os.path.join(fs.base_location, path))
    if not path.startswith(fs.base_location):
        raise ValueError("Invalid file path detected!")
    return path


def _list_transaction_dir(transaction_uuid):
    transaction_uuid = str(transaction_uuid)
    if transaction_uuid not in fs.listdir("")[0]:
        os.makedirs(os.path.join(fs.base_location, transaction_uuid), exist_ok=True)
        return [], []
    return fs.listdir(os.path.normpath(transaction_uuid))


def _get_file_from_transaction(transaction_uuid, file_name):
    transaction_uuid = str(transaction_uuid)
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


def _put_file_in_transaction(
    transaction_uuid, file_name, file_content, overwrite=False, path=""
):
    transaction_uuid = str(transaction_uuid)
    dir_path = os.path.join(transaction_uuid, path.strip("/"))
    dir_path_abs = os.path.join(fs.base_location, dir_path)
    os.makedirs(dir_path_abs, exist_ok=True)

    file_rel_path = os.path.join(dir_path, file_name)
    file_abs_path = _sanitize_path(os.path.join(dir_path_abs, file_name))

    if fs.exists(file_abs_path):
        if not overwrite:
            return False
        fs.delete(file_rel_path)

    file_content = File(file_content)
    if file_content.size > MAX_FILE_SIZE:
        return False

    return fs.save(file_rel_path, file_content)


@require_auth
def upload_transactions_invoice(request, transaction_uuid):
    transaction_uuid = str(transaction_uuid)
    user_group = request.session["auth"]["group"]
    relative_path = f"/{transaction_uuid}/invoice/"

    if not is_writable(relative_path, user_group):
        return HttpResponseForbidden(
            _("You don't have permission to upload files here.").encode("utf-8")
        )

    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        success = _put_file_in_transaction(
            transaction_uuid, uploaded_file.name, uploaded_file.file, path="invoice/"
        )

        if not success:
            messages.error(request, _("Failed to upload file."))
        else:
            messages.success(request, _("File uploaded successfully"))

        return render(
            request,
            "upload_file.html",
            {
                "transaction_uuid": transaction_uuid,
                "file_name": uploaded_file.name,
            },
        )

    return render(request, "upload_file.html", {"transaction_uuid": transaction_uuid})


@require_auth
def transaction_files(request, transaction_uuid):
    transaction_uuid = str(transaction_uuid)
    user_group = request.session["auth"]["group"]
    relative_path = f"/{transaction_uuid}/"

    if not is_readable(relative_path, user_group):
        return HttpResponseForbidden(
            "You don't have permission to view these files.".encode("utf-8")
        )

    admin_url = "admin/" if _is_admin(request) or _is_support(request) else ""

    if user_group in (CLIENT_GROUPS + ADMIN_GROUPS + SUPPORT_GROUPS):
        _, error = _make_api_request(
            f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/",
            headers=_get_headers(request),
        )
        if error:
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


@require_auth
def browse_transaction_dir(request, transaction_uuid, directory_name=None):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        success = _put_file_in_transaction(
            transaction_uuid,
            uploaded_file.name,
            uploaded_file.file,
            path=directory_name + "/" if directory_name else "",
        )
        if not success:
            messages.error(request, "Failed to upload.")
        else:
            messages.success(request, "Upload successful.")
            payload = {
                "time": "",
                "dirName": "",
                "path": "",
            }
            _make_api_request(
                f"{API_BASE_URL}/{transaction_uuid}/upload-event",
                method=requests.post,
                headers=_get_headers(request),
                body=payload,
            )
        return redirect(request.path)
    transaction_uuid = str(transaction_uuid)
    directory_name = directory_name or ""
    user_group = request.session["auth"]["group"]

    transaction_root, error = _make_api_request(
        f"{API_BASE_URL}/transactions/{transaction_uuid}/file-name",
        headers=_get_headers(request),
    )
    if error:
        return error

    rel_path = (
        f"/{transaction_uuid}/{directory_name}/"
        if directory_name
        else f"/{transaction_uuid}/"
    )

    if not is_readable(rel_path, user_group):
        return HttpResponseForbidden(
            "You don't have permission to view this directory.".encode("utf-8")
        )

    full_path = (
        os.path.join(transaction_uuid, directory_name)
        if directory_name
        else transaction_uuid
    )
    if transaction_uuid not in fs.listdir(".")[0]:
        os.makedirs(os.path.join(fs.base_location, transaction_uuid), exist_ok=True)
        for directory in DIRECTORIES:
            os.makedirs(
                os.path.join(fs.base_location, transaction_uuid, directory),
                exist_ok=True,
            )
    try:
        dir_list, file_list = fs.listdir(full_path)
    except FileNotFoundError:
        dir_list, file_list = [], []

    return render(
        request,
        "file_browser.html",
        {
            "transaction_uuid": transaction_uuid,
            "transaction_root": transaction_root["name"],
            "directory_name": directory_name,
            "dir_list": dir_list,
            "file_list": file_list,
            "is_writable": is_writable(rel_path, user_group),
        },
    )


@require_auth
def file_interaction(request, transaction_uuid, file_name, directory_name=None):
    transaction_uuid = str(transaction_uuid)
    directory_name = directory_name or ""
    user_group = request.session["auth"]["group"]

    relative_path = f"{transaction_uuid}/{directory_name}/{file_name}"
    file_abs_path = fs.path(relative_path)

    if not is_readable(relative_path, user_group):
        return HttpResponseForbidden(
            "You don't have permission to access this file.".encode("utf-8")
        )

    if request.method == "GET" and "download" in request.GET:
        if not os.path.exists(file_abs_path):
            raise Http404("File not found.")

        with fs.open(relative_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/octet-stream")
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
            return response

    elif request.method == "GET" and "delete" in request.GET:
        if not is_writable(relative_path, user_group):
            return HttpResponseForbidden(
                "You don't have permission to delete this file.".encode("utf-8")
            )

        if not os.path.exists(file_abs_path):
            raise Http404("File not found.")

        fs.delete(relative_path)
        messages.success(request, _("File deleted successfully"))
        return redirect(
            "browse_transaction_folder",
            transaction_uuid=transaction_uuid,
            directory_name=directory_name,
        )
    messages.warning(request, _("Invalid request"))
    return redirect(
        "browse_transaction_folder",
        transaction_uuid=transaction_uuid,
        directory_name=directory_name,
    )
