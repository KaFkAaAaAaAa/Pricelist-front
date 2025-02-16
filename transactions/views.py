from math import floor

import requests
from django.http.response import HttpResponseForbidden
from django.shortcuts import redirect, render

from Pricelist.settings import ADMIN_GROUPS, API_BASE_URL
from Pricelist.views import _get_auth


def offer(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if request.method == "POST":
        payload = {
            "description": request.POST["order_description"],
            "itemsOrdered": request.session["current_offer"],
        }
        for item in payload["itemsOrdered"]:
            item["price"] = int(floor(100 * float(item.get("price"))))
            item["amount"] = int(floor(10 * float(item.get("amount"))))
        response = requests.post(
            f"{API_BASE_URL}/orders/", headers=headers, json=payload
        )
        if response.status_code == 200:
            request.session["current_offer"] = []
            request.session.modified = True
            return redirect("price_list")
        # TODO: weird bug, after getting error from api the prices arent formatted well

    return render(request, "offer.html")


def delete_from_offer(request, item_sku):
    item_skus = [item.get("sku") for item in request.session["current_offer"]]
    index = item_skus.index(item_sku)
    if index is not None:
        request.session["current_offer"].pop(index)
        request.session.modified = True
    return redirect("offer")


def edit_item_offer(request, item_sku):
    item_skus = [item.get("sku") for item in request.session["current_offer"]]
    index = item_skus.index(item_sku)
    if index is None:
        return redirect("offer")
    if request.method == "POST":
        request.session["current_offer"][index]["amount"] = request.POST["amount"]
        request.session["current_offer"][index]["additionalInfo"] = request.POST[
            "additionalInfo"
        ]
    item = request.session.get("current_offer")[index]
    request.session.modified = True
    if request.method == "POST":
        return redirect("offer")
    return render(request, "edit_item_offer.html", {"item": item})


def client_orders(request, user_id):
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

    response = requests.get(
        f"{API_BASE_URL}/orders/admin/client/{user_id}/", headers=headers
    )
    orders = response.json()
    for order in orders:
        if order["orderStatusHistory"]:
            order["status"] = order["orderStatusHistory"][-1]["status"]
            order["status_time"] = order["orderStatusHistory"][-1]["time"]
        else:
            order["status"] = "none"
            order["status_time"] = "none"
    return render(request, "order_list.html", {"orders": orders})


def admin_order_detail(request, order_id):
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

    msg = {}

    if request.method == "POST":
        # TODO: Payload
        payload = {}
        response = requests.post(
            f"{API_BASE_URL}/orders/admin/{order_id}/",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            msg["err"] = "Error! Something went wrong"
        else:
            msg["suc"] = "transaction data changed successfully"

    response = requests.get(f"{API_BASE_URL}/orders/admin/{order_id}/", headers=headers)
    order = response.json()

    return render(request, "order_detail_admin.html", {"order": order, "msg": msg})
