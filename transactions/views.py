import copy
from datetime import datetime
from math import floor

import requests
from django.http import (
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.http.response import HttpResponseForbidden
from django.shortcuts import redirect, render

from items.views import _add_items_to_offer, _make_price_list
from pdfgenerator.views import generate_pdf
from Pricelist.settings import ADMIN_GROUPS, API_BASE_URL, CLIENT_GROUPS
from Pricelist.views import (
    _amount_to_display,
    _amount_to_float,
    _amount_to_store,
    _api_error_interpreter,
    _get_auth,
    _price_to_display,
    _price_to_float,
    _price_to_store,
)
from transactions.forms import ItemForm


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
    """calculates total for each item in item_list based on item.price
    and item.amount, saves it in item["total"] and returns total of totals"""

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
    if transaction["transactionStatusHistory"]:
        transaction["status"] = transaction["transactionStatusHistory"][-1]["status"]
        transaction["status_time"] = _parse_date(
            transaction["transactionStatusHistory"][-1]["time"]
        )
    else:
        transaction["status"] = "none"
        transaction["status_time"] = "none"
    return transaction


def _current_offer_to_payload(current_offer):
    payload = []
    for item in current_offer:
        payload.append(
            {
                "sku": item["sku"],
                "name": item["name"],
                "price": _price_to_store(item["price"]),
                "amount": _amount_to_store(item["amount"]),
                "additionalInfo": item["additionalInfo"],
            }
        )
    return payload


def offer(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if "current_offer" not in request.session.keys():
        request.session["current_offer"] = []

    if request.method == "POST" and auth["group"] not in ADMIN_GROUPS:
        payload = {
            "description": request.POST["transaction_description"],
            "itemsOrdered": _current_offer_to_payload(request.session["current_offer"]),
        }
        # items already converted to "store" values
        response = requests.post(
            f"{API_BASE_URL}/transactions/", headers=headers, json=payload
        )
        if response.status_code == 200:
            request.session["current_offer"] = []
            request.session.modified = True
            return redirect("client_transaction_detail", response.json()["uuid"])
        # TODO: weird bug, after getting error from api the
        # prices aren't formatted well

    offer = request.session.get("current_offer")
    totals = _get_stored_item_list_to_display(offer)
    client_emails = []  # here bc unbound
    if auth["group"] in ADMIN_GROUPS:
        response = requests.get(
            f"{API_BASE_URL}/clients/admin/admin-list/groups/",
            headers=headers,
        )
        clients_auths = response.json()

        for client, client_auth in zip(
            clients_auths["clients"], clients_auths["auths"]
        ):
            if client_auth["authGroup"] in CLIENT_GROUPS:
                # TODO: two clients same company
                client_emails.append(client["clientCompanyName"])
        if request.method == "POST":
            client_uuid = ""
            for client in clients_auths["clients"]:
                if client["clientCompanyName"] == request.POST["client"]:
                    client_uuid = client["id"]
            if not client_uuid:
                return HttpResponseServerError(b"Internal Server Error")

            payload = {
                "description": request.POST["transaction_description"],
                "itemsOrdered": _current_offer_to_payload(
                    request.session["current_offer"]
                ),
                "clientUUID": client_uuid,
            }
            # items already converted to "store" values
            response = requests.post(
                f"{API_BASE_URL}/transactions/admin/", headers=headers, json=payload
            )
            if response.status_code == 200:
                request.session["current_offer"] = []
                request.session.modified = True
                return redirect("admin_transaction_detail", response.json()["uuid"])

    return render(
        request,
        "offer.html",
        {"offer": offer, "totals": totals, "clients": client_emails},
    )


def offer_list(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if auth["group"] not in ADMIN_GROUPS + CLIENT_GROUPS:
        return HttpResponseForbidden(
            "<h1>You do not have access to that page<h1>".encode("utf-8")
        )

    if request.method == "POST":
        return _add_items_to_offer(request, headers)

    return _make_price_list(request, headers, pattern="offer_list.html")


def delete_from_offer(request, item_sku):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    item_skus = [item.get("sku") for item in request.session["current_offer"]]
    index = item_skus.index(item_sku)
    if index is not None:
        request.session["current_offer"].pop(index)
        request.session.modified = True
    return redirect("offer")


def add_new_item_to_transaction(request, transaction_uuid):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            payload = {
                "sku": form.cleaned_data["sku"],
                "name": form.cleaned_data["name"],
                "price": _price_to_store(form.cleaned_data["price"]),
                "amount": _amount_to_store(form.cleaned_data["amount"]),
                "additionalInfo": form.cleaned_data["additionalInfo"],
            }
            print(payload)
            admin_url = "admin/" if auth["group"] in ADMIN_GROUPS else ""
            response = requests.post(
                f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/add-item/",
                headers=auth["headers"],
                json=payload,
            )
            if response.status_code == 200:
                if admin_url:
                    return redirect("admin_transaction_detail", response.json()["uuid"])

    form = ItemForm()
    return render(
        request,
        "new_item_transaction.html",
        {
            "form": form,
        },
    )


def edit_item_offer(request, item_sku):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

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

    response = requests.get(f"{API_BASE_URL}/transactions/", headers=headers)

    transactions = response.json()
    for transaction in transactions:
        _set_status(transaction)
        transaction["totals"] = _get_stored_item_list_to_display(
            transaction["transactionItemsOrdered"],
            key_p="itemOrderedPrice",
            key_a="itemOrderedAmount",
        )
    return render(request, "transaction_list.html", {"transactions": transactions})


def admin_transactions(request):
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

    response = requests.get(f"{API_BASE_URL}/transactions/admin/", headers=headers)
    transactions = response.json()
    for transaction in transactions:
        _set_status(transaction)
        transaction["totals"] = _get_stored_item_list_to_display(
            transaction["transactionItemsOrdered"],
            key_p="itemOrderedPrice",
            key_a="itemOrderedAmount",
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
        f"{API_BASE_URL}/transactions/admin/client/{user_id}/", headers=headers
    )
    transactions = response.json()
    for transaction in transactions:
        _set_status(transaction)
        transaction["totals"] = _get_stored_item_list_to_display(
            transaction["transactionItemsOrdered"],
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
            f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            msg["err"] = "Error! Something went wrong"
        else:
            msg["suc"] = "transaction data changed successfully"

    response = requests.get(
        f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/", headers=headers
    )
    transaction = response.json()
    transaction = _set_status(transaction)
    transaction["totals"] = _get_stored_item_list_to_display(
        transaction["transactionItemsOrdered"],
        key_p="itemOrderedPrice",
        key_a="itemOrderedAmount",
    )

    return render(
        request,
        "transaction_detail_admin.html",
        {"transaction": transaction, "msg": msg},
    )


def edit_transaction_item(request, transaction_uuid, item_sku):
    """edit item in transaction for both admin and user, function chooses
    if it should behave as admin or client based on"""
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    admin_url = "admin/" if auth["group"] in ADMIN_GROUPS else ""

    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            payload = {
                "sku": form.cleaned_data["sku"],
                "name": form.cleaned_data["name"],
                "price": _price_to_store(form.cleaned_data["price"]),
                "amount": _amount_to_store(form.cleaned_data["amount"]),
                "additionalInfo": form.cleaned_data["additionalInfo"],
            }
            response = requests.put(
                f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/{item_sku}",
                headers=auth["headers"],
                json=payload,
            )
            if response.status_code == 200:
                if admin_url:
                    return redirect("admin_transaction_detail", transaction_uuid)
                return redirect("transaction_detail", transaction_uuid)

    response = requests.get(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/",
        headers=auth["headers"],
    )

    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    transaction = response.json()

    item = None
    for item_obj in transaction["transactionItemsOrdered"]:
        if item_obj.get("itemOrderedSku") == item_sku:
            item = item_obj
            break
    if not item:
        return HttpResponseNotFound
    form = ItemForm(
        initial={
            "sku": item["itemOrderedSku"],
            "name": item["itemOrderedName"],
            "price": _price_to_float(item["itemOrderedPrice"]),
            "amount": _amount_to_float(item["itemOrderedAmount"]),
            "additionalInfo": item["itemOrderedAdditionalInfo"],
        }
    )

    return render(
        request,
        "new_item_transaction.html",
        {
            "form": form,
            "title": "Edit item",
        },
    )


def delete_transaction_item(request, transaction_uuid, item_sku):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    admin_url = "admin/" if auth["group"] in ADMIN_GROUPS else ""

    response = requests.delete(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/{item_sku}",
        headers=auth["headers"],
    )

    if response.status_code != 200:
        print("error in delete function")

    return redirect("admin_transaction_detail", transaction_uuid)


def print_transaciton(request, transaction_uuid):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    admin_url = "admin/" if auth["group"] in ADMIN_GROUPS else ""

    response = requests.get(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/",
        headers=headers,
    )

    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    transaction = response.json()
    totals = _get_stored_item_list_to_display(
        transaction["transactionItemsOrdered"],
        key_a="itemOrderedAmount",
        key_p="itemOrderedPrice",
    )
    transaction = _set_status(transaction)
    data = {
        "items": transaction["transactionItemsOrdered"],
        "client": transaction["transactionClient"],
        "total": totals,
        "date": transaction["status_time"],
    }

    status = transaction["status"]

    if status == "OFFER":
        return print_offer(request, data)
    if status == "PROGNOSE":
        return print_prognose(data)
    if status == "FINAL":
        return print_final(data)
    if status == "PROPOSITION":
        return HttpResponseBadRequest(b"Proposition cannot be printed")

    return HttpResponseServerError


def print_offer(request, data):
    return generate_pdf(request, "pdf_offer.html", data)


def print_prognose(data):
    pass


def print_final(data):
    pass


def delete_transaction(request, transaction_uuid):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if auth.get("group") not in ADMIN_GROUPS:
        response = requests.delete(
            f"{API_BASE_URL}/transactions/{transaction_uuid}/", headers=headers
        )
    else:
        response = requests.delete(
            f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/", headers=headers
        )
    redir_url = request.headers.get("referer")
    err = ""
    if response.status_code != 200:
        err = "Error!"
    return redirect(redir_url)
