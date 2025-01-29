from django.shortcuts import render
from Pricelist.views import *
import requests
from django.shortcuts import render, redirect
from Pricelist.views import _get_auth, API_BASE_URL


def admin_list(request, msg=None):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    # GET REQ
    err = ""
    admins = []
    response = requests.get(f"{API_BASE_URL}/users/admin/admins/", headers=headers)
    try:
        admins = response.json()
        if not admins:
            err = "No admin users in database"
    except:
        err = "API error"

    return render(
        request, "admin_list.html", {"admins": admins, "msg": msg, "err": err}
    )


def delete_admin(request, admin_id):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if not isinstance(admin_id, UUID):
        raise Http404

    response = requests.delete(
        f"{API_BASE_URL}/users/admin/{admin_id}", headers=headers
    )

    if response.status_code == 200:
        try:
            return redirect("admin_list", msg="Admin deleted successfully")
        except:
            return redirect("admin_list")

    elif response.status_code == 404:
        raise Http404
    else:
        try:
            return redirect("admin_list", "API ERROR!")
        except:
            return redirect("admin_list")


def edit_admin(request, admin_id):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if auth.get("group") not in ADMIN_GROUPS:
        return HttpResponseForbidden(
            "<h1>You do not have access to that page<h1>".encode("utf-8")
        )

    if request.method == "POST":
        payload_admin = {
            "userLastName": request.POST["userLastName"],
            "userFirstName": request.POST["userFirstName"],
            "userEmail": request.POST["userEmail"],
            "userTelephoneNumber": request.POST["userTelephoneNumber"],
        }

        response = requests.put(
            f"{API_BASE_URL}/users/admin/{admin_id}", json=payload_admin
        )

        if response.status_code == 200:
            return redirect("admin_list")
        else:
            # TODO: user might want to know what went wrong
            error = "Something went wrong!"
            return render(request, "edit_admin.html", {"err": error})

    try:
        admin = requests.get(f"{API_BASE_URL}/users/admin/{admin_id}").json()
    except:
        return render(request, "edit_admin.html", {"err": "API ERROR!"})

    return render(request, "edit_admin.html", {"admin": admin})
