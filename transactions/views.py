import copy
from datetime import datetime
from math import floor

import requests
from django.http.response import HttpResponseForbidden
from django.shortcuts import redirect, render

from Pricelist.settings import ADMIN_GROUPS, API_BASE_URL, CLIENT_GROUPS
from Pricelist.views import (
    _amount_to_display,
    _amount_to_store,
    _get_auth,
    _price_to_display,
    _price_to_store,
)


def _calculate_total_mass(item_list, key="amount") -> float:
    """calculates total mass of item_list by item.amount"""

    mass = 0
    if len(item_list) == 0:
        return 0
    for item in item_list:
        if item.get(key):
            mass += item.get(key)
    return mass


def _calculate_total_price(item_list, key_p="price", key_a="amount") -> float:
    """calculates total for each item in item_list based on item.price and item.amount,
    saves it in item["total"] and returns total of totals"""

    price = 0
    if len(item_list) == 0:
        return 0
    for item in item_list:
        if not item.get(key_p) or not item.get(key_a):
            item["total"] = 0
            continue
        item["total"] = item.get(key_p) * item.get(key_a)
        price += item.get("total")
    return price


def _get_stored_item_list_to_display(item_list, key_p="price", key_a="amount") -> dict:
    price = 0
    mass = 0
    for item in item_list:
        item["total"] = floor(item.get(key_p) * item.get(key_a) / 10)
        price += item.get("total")
        mass += item.get(key_a)
        item["total"] = _price_to_display(item.get("total"))
        item[key_p] = _price_to_display(item.get(key_p))
        item[key_a] = _amount_to_display(item.get(key_a))
    return {
        "mass": _amount_to_display(mass),
        "price": _price_to_display(price),
    }


def _parse_date(date: str) -> datetime:
    return datetime.fromisoformat(date)


def _set_status(transaction) -> dict:
    if transaction["orderStatusHistory"]:
        transaction["status"] = transaction["orderStatusHistory"][-1]["status"]
        transaction["status_time"] = _parse_date(
            transaction["orderStatusHistory"][-1]["time"]
        )
    else:
        transaction["status"] = "none"
        transaction["status_time"] = "none"
    return transaction


def offer(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if not "current_offer" in request.session.keys():
        return redirect("price_list")

    if request.method == "POST" and auth["group"] not in ADMIN_GROUPS:
        payload = {
            "description": request.POST["order_description"],
            "itemsOrdered": request.session["current_offer"],
        }
        # items already converted to "store" values
        response = requests.post(
            f"{API_BASE_URL}/orders/", headers=headers, json=payload
        )
        if response.status_code == 200:
            request.session["current_offer"] = []
            request.session.modified = True
            return redirect("price_list")
        # TODO: weird bug, after getting error from api the prices arent formatted well

    offer = request.session.get("current_offer")
    totals = _get_stored_item_list_to_display(offer)
    client_emails = []
    if auth["group"] in ADMIN_GROUPS:
        response = requests.get(
            f"{API_BASE_URL}/clients/admin/admin-list/groups/",
            headers=headers,
        )
        __import__('pdb').set_trace()
        clients_auths = response.json()

        for (client, client_auth) in zip(clients_auths["clients"], clients_auths["auths"]):
            if client_auth["authGroup"] in CLIENT_GROUPS:
                client_emails.append(client["clientCompanyName"])
        if request.method == "POST":
            # TEST and finish admins offer creation
            pass

    return render(request, "offer.html", {"offer": offer, "totals": totals, "clients": client_emails})


def delete_from_offer(request, item_sku):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    item_skus = [item.get("sku") for item in request.session["current_offer"]]
    index = item_skus.index(item_sku)
    if index is not None:
        request.session["current_offer"].pop(index)
        request.session.modified = True
    return redirect("offer")


def edit_item_offer(request, item_sku):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    item_skus = [item.get("sku") for item in request.session["current_offer"]]
    index = item_skus.index(item_sku)
    if index is None:
        return redirect("offer")
    if request.method == "POST":
        request.session["current_offer"][index]["price"] = _price_to_store(
            request.POST["amount"]
        )
        request.session["current_offer"][index]["amount"] = _amount_to_store(
            request.POST["amount"]
        )
        request.session["current_offer"][index]["additionalInfo"] = request.POST[
            "additionalInfo"
        ]
    item = copy.deepcopy(request.session.get("current_offer")[index])
    item["amount"] = _amount_to_display(item["amount"])
    item["price"] = _price_to_display(item["price"])
    request.session.modified = True
    if request.method == "POST":
        return redirect("offer")
    return render(request, "edit_item_offer.html", {"item": item})


def client_transactions(request):

    # this is nearly the same func as the one below
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    response = requests.get(f"{API_BASE_URL}/orders/", headers=headers)

    transactions = response.json()
    for transaction in transactions:
        _set_status(transaction)
        transaction["totals"] = (
            _calculate_total_price(transaction["orderItemsOrdered"]),
            _calculate_total_mass(transaction["orderItemsOrdered "]),
        )
    return render(request, "transaction_list.html", {"transactions": transactions})


def admin_client_transactions(request, user_id):
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
    transactions = response.json()
    for transaction in transactions:
        _set_status(transaction)
        transaction["totals"] = _get_stored_item_list_to_display(
            transaction["orderItemsOrdered"],
            key_p="itemOrderedPrice",
            key_a="itemOrderedAmount",
        )

    return render(request, "transaction_list.html", {"transactions": transactions})


def admin_transaction_detail(request, transaction_uuid):
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
            f"{API_BASE_URL}/orders/admin/{transaction_uuid}/",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            msg["err"] = "Error! Something went wrong"
        else:
            msg["suc"] = "transaction data changed successfully"

    response = requests.get(
        f"{API_BASE_URL}/orders/admin/{transaction_uuid}/", headers=headers
    )
    transaction = response.json()
    transaction = _set_status(transaction)
    transaction["totals"] = _get_stored_item_list_to_display(
        transaction["orderItemsOrdered"],
        key_p="itemOrderedPrice",
        key_a="itemOrderedAmount",
    )

    return render(
        request,
        "transaction_detail_admin.html",
        {"transaction": transaction, "msg": msg},
    )


def delete_transaction(request, transaction_uuid):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if auth.get("group") not in ADMIN_GROUPS:
        response = requests.delete(
            f"{API_BASE_URL}/orders/{transaction_uuid}/", headers=headers
        )
    else:
        response = requests.delete(
            f"{API_BASE_URL}/orders/admin/{transaction_uuid}/", headers=headers
        )
    redir_url = request.headers.get("referer")
    err = ""
    if response.status_code != 200:
        err = "Error!"
    return redirect(redir_url)
