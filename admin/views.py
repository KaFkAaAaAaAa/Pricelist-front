import logging
from uuid import UUID

import requests
from django.contrib import messages
from django.http import HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from Pricelist.settings import ADMIN_GROUPS, API_BASE_URL
from Pricelist.utils import _get_headers, _make_api_request, require_auth, require_group

logger = logging.getLogger(__name__)


@require_auth
@require_group(ADMIN_GROUPS)
def admin_list(request, msg=None):

    # GET REQ
    err = ""
    admins = []
    response = requests.get(
        f"{API_BASE_URL}/users/admin/admins/", headers=_get_headers(request)
    )
    try:
        admins = response.json()
        if not admins:
            err = "No admin users in database"
    except:
        err = "API error"

    return render(
        request, "admin_list.html", {"admins": admins, "msg": msg, "err": err}
    )


@require_auth
@require_group(ADMIN_GROUPS)
def delete_admin(request, admin_id):
    if not isinstance(admin_id, UUID):
        return HttpResponseNotFound(_("Admin not found").encode("UTF-8"))

    headers = _get_headers(request)

    response = requests.delete(
        f"{API_BASE_URL}/users/admin/{admin_id}", headers=headers
    )

    if response.status_code == 200:
        try:
            return redirect("admin_list", msg="Admin deleted successfully")
        except:
            return redirect("admin_list")

    elif response.status_code == 404:
        return HttpResponseNotFound(_("Admin not found").encode("UTF-8"))
    else:
        try:
            return redirect("admin_list", "API ERROR!")
        except:
            return redirect("admin_list")


@require_auth
@require_group(ADMIN_GROUPS)
def user_logins_list(request):
    headers = _get_headers(request)

    last_logged_in_page = parse_logs_login_action(page_no, page_size)

    return render(request, "user_logins_list.html", {"last_logged_in": last_logged_in})


@require_auth
@require_group(ADMIN_GROUPS)
def edit_admin(request, admin_id):

    headers = _get_headers(request)

    if request.method == "POST":
        payload_admin = {
            "userLastName": request.POST["userLastName"],
            "userFirstName": request.POST["userFirstName"],
            "userEmail": request.POST["userEmail"],
            "userTelephoneNumber": request.POST["userTelephoneNumber"],
        }

        response = requests.put(
            f"{API_BASE_URL}/users/admin/{admin_id}",
            json=payload_admin,
            headers=headers,
        )

        if response.status_code == 200:
            return redirect("admin_list")
        # TODO: user might want to know what went wrong
        messages.error(request, "{_('Internal Server Error')}!")
        return render(request, "edit_admin.html")

    admin, error = _make_api_request(
        f"{API_BASE_URL}/users/admin/{admin_id}", headers=headers
    )
    if error:
        return error
    return render(request, "edit_admin.html", {"admin": admin})
