import copy
from datetime import datetime
from math import floor

import requests
from django.http import (
    HttpResponse,
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
    _make_api_request,
    _price_to_display,
    _price_to_float,
    _price_to_store,
)
from transactions.forms import ItemForm, PrognoseFrom


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


def _parse_transaction_edit_items(request):
    """function parses post parameters in format {field}-{item-uuid}
    returns item list and alku dictionary {"uuid": value}"""
    items = {}
    alku = {}
    for param in request.POST:
        if param.find("-") == -1:
            continue
        field, uuid = param.split("-", 1)
        if not (field and uuid):
            continue
        if uuid not in items:
            items[uuid] = {"uuid": uuid}
        value = request.POST[param]
        if field == "amount":
            value = _amount_to_store(value)
        if field == "price":
            value = _price_to_store(value)
        if field == "alku":
            alku[uuid] = _amount_to_store(value)
        else:
            items[uuid][field] = value
    return list(items.values()), alku


def _set_status(transaction) -> dict:
    if transaction["statusHistory"]:
        transaction["status"] = transaction["statusHistory"][-1]["status"]
        transaction["status_time"] = _parse_date(
            transaction["statusHistory"][-1]["time"]
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
    client_company_names = []  # here bc unbound
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
                client_company_names.append(client["clientCompanyName"])
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
                "clientId": client_uuid,
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
        {"offer": offer, "totals": totals, "clients": client_company_names},
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
        if "itemsOrdered" in transaction.keys():
            transaction["totals"] = _get_stored_item_list_to_display(
                transaction["itemsOrdered"]
            )
        else:
            transaction["totals"] = {
                "mass": 0,
                "price": 0,
            }

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
        if "itemsOrdered" in transaction.keys():
            transaction["totals"] = _get_stored_item_list_to_display(
                transaction["itemsOrdered"]
            )
        else:
            transaction["totals"] = {
                "mass": 0,
                "price": 0,
            }

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
        if "itemsOrdered" in transaction.keys():
            transaction["totals"] = _get_stored_item_list_to_display(
                transaction["itemsOrdered"]
            )
        else:
            transaction["totals"] = {
                "mass": 0,
                "price": 0,
            }

    return render(request, "transaction_list.html", {"transactions": transactions})


def edit_details(request, transaction):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]


def admin_transaction_detail(request, transaction_uuid):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    # if auth.get("group") not in ADMIN_GROUPS:
    #     return HttpResponseForbidden(
    #         "<h1>You do not have access to that page<h1>".encode("utf-8")
    #     )

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
        transaction["itemsOrdered"],
    )
    if transaction["status"] in ("PROGNOSE", "FINAL"):
        response = requests.get(
            f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
            headers=headers,
        )
        error = _api_error_interpreter(response.status_code)
        if error:
            return error

        transaction_details = response.json()
        return render(
            request,
            "transaction_detail_admin.html",
            {
                "transaction": transaction,
                "transactionDetails": transaction_details,
                "msg": msg,
            },
        )

    return render(
        request,
        "transaction_detail_admin.html",
        {
            "transaction": transaction,
            "msg": msg,
        },
    )


def edit_transaction_item(request, transaction_uuid, item_uuid):
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
                f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/{item_uuid}",
                headers=auth["headers"],
                json=payload,
            )
            if response.status_code == 200:
                if admin_url:
                    return redirect("admin_transaction_detail", transaction_uuid)
                return redirect("client_transaction_detail", transaction_uuid)

    response = requests.get(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/",
        headers=auth["headers"],
    )

    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    transaction = response.json()

    item = None
    for item_obj in transaction["itemsOrdered"]:
        if item_obj.get("uuid") == str(item_uuid):
            item = item_obj
            break
    if not item:
        return HttpResponseNotFound()
    form = ItemForm(
        initial={
            "sku": item["sku"],
            "name": item["name"],
            "price": _price_to_float(item["price"]),
            "amount": _amount_to_float(item["amount"]),
            "additionalInfo": item["additionalInfo"],
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


def delete_transaction_item(request, transaction_uuid, item_uuid):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    admin_url = "admin/" if auth["group"] in ADMIN_GROUPS else ""

    response = requests.delete(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/{item_uuid}",
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
    totals = _get_stored_item_list_to_display(transaction["itemsOrdered"])
    transaction = _set_status(transaction)

    if admin_url:
        response_client = requests.get(
            f"{API_BASE_URL}/clients/{admin_url}{transaction['clientId']}/",
            headers=headers,
        )
    else:
        response_client = request.session["logged_user"]

    error = _api_error_interpreter(response_client.status_code)
    if error:
        return error

    data = {
        "items": transaction["itemsOrdered"],
        "client": response_client.json(),
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

    return HttpResponseServerError()


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


def create_offer(request, data, headers):
    if "user" in request.session["logged_user"].keys():
        return HttpResponseForbidden()
    uuid = data["transaction_uuid"]
    response = requests.get(
        f"{API_BASE_URL}/transactions/admin/{uuid}/update-status/?status=offer",
        headers=headers,
    )
    error = _api_error_interpreter(response.status_code)
    if error:
        return error
    return redirect("admin_transaction_detail", data["transaction_uuid"])


def create_prognose(request, data, headers):
    plates = []

    if request.method == "POST":
        form = PrognoseFrom(request.POST)
        if form.is_valid():
            plates = (
                form.cleaned_data["plates_list"].split(",")
                if form.cleaned_data["plates_list"]
                else []
            )
            payload = {
                "plates": (
                    form.cleaned_data["plates_list"].split(",")
                    if form.cleaned_data["plates_list"]
                    else []
                ),
                "transportCost": int(form.cleaned_data["delivery_price"]),
                "informations": {
                    "additional_info": form.cleaned_data["prognose_info"],
                    "delivery_info": form.cleaned_data["delivery_info"],
                    "delivery_date": str(form.cleaned_data["delivery_date"]),
                },
            }
            uuid = data["transaction_uuid"]
            response = requests.post(
                f"{API_BASE_URL}/transaction-details/admin/{uuid}/",
                headers=headers,
                json=payload,
            )
            error = _api_error_interpreter(response.status_code)
            if error:
                return error
            response = requests.get(
                f"{API_BASE_URL}/transactions/admin/{uuid}/update-status/?status=prognose",
                headers=headers,
            )
            error = _api_error_interpreter(response.status_code)
            if error:
                return error
            return redirect("admin_transaction_detail", data["transaction_uuid"])
    else:
        form = PrognoseFrom()

    return render(request, "create_prognose.html", {"form": form, "plates": plates})


def create_final(request, data, headers):
    uuid = data["transaction_uuid"]
    if request.method == "POST":
        items, alku = _parse_transaction_edit_items(request)
        response = requests.put(
            f"{API_BASE_URL}/transactions/admin/{uuid}/",
            json={"itemsOrdered": items},
            headers=headers,
        )
        error = _api_error_interpreter(response.status_code)
        if error:
            return error

        response = requests.put(
            f"{API_BASE_URL}/transaction-details/admin/{uuid}/",
            json={"alkuAmount": alku},
            headers=headers,
        )
        error = _api_error_interpreter(response.status_code)
        if error:
            return error

        response = requests.get(
            f"{API_BASE_URL}/transactions/admin/{uuid}/update-status/?status=final",
            headers=headers,
        )
        error = _api_error_interpreter(response.status_code)
        if error:
            return error
        return redirect("admin_transaction_detail", data["transaction_uuid"])

    response = requests.get(
        f"{API_BASE_URL}/transaction-details/admin/{uuid}/",
        headers=headers,
    )
    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    data["transactionDetails"] = response.json()
    return render(request, "create_final.html", data)


def change_status(request, transaction_uuid):
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
    totals = _get_stored_item_list_to_display(transaction["itemsOrdered"])
    transaction = _set_status(transaction)
    status = transaction["status"]

    if admin_url:
        response_client = requests.get(
            f"{API_BASE_URL}/clients/{admin_url}{transaction['clientId']}",
            headers=headers,
        )
        error = _api_error_interpreter(response_client.status_code)
        if error:
            return error
    else:
        response_client = request.session["logged_user"]

    # TODO: cleanup
    data = {
        "transaction": transaction,
        "items": transaction["itemsOrdered"],
        "client": response_client.json(),
        "total": totals,
        "date": transaction["status_time"],
        "transaction_uuid": transaction_uuid,
    }

    if status == "PROPOSITION":
        return create_offer(request, data, headers)
    if status == "OFFER":
        return create_prognose(request, data, headers)
    if status == "PROGNOSE":
        return create_final(request, data, headers)
    if status == "FINAL":
        return HttpResponseBadRequest(b"Order has already been finalised")


def new_transaction_detail(request, transaction_uuid):
    # if post -> edit transaction/transaction details
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    msg = {}

    admin_url = "admin/" if auth["group"] in ADMIN_GROUPS else ""

    if request.method == "POST":
        items, alku = _parse_transaction_edit_items(request)
        payload = {"itemsOrdered": items}
        response, error = _make_api_request(
            f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/",
            method=requests.put,
            headers=headers,
            body=payload,
        )
        if error:
            return error

    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/", headers=headers
    )
    if error:
        return error

    transaction = _set_status(transaction)
    transaction["totals"] = _get_stored_item_list_to_display(
        transaction["itemsOrdered"],
    )
    data = {
        "transaction": transaction,
        "msg": msg,
    }
    if transaction["status"] in ("PROGNOSE", "FINAL"):
        transaction_details, error = _make_api_request(
            f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
            headers=headers,
        )
        if error:
            return error

        if transaction["status"] == "FINAL" and transaction_details["alkuAmount"]:
            for item in transaction["itemsOrdered"]:
                try:
                    item["alku"] = transaction_details["alkuAmount"][item["uuid"]]
                except KeyError:
                    continue
        # with __setitem__ instead of data['transactionDetails']
        # it doesn't make any warnings
        data.__setitem__("transactionDetails", transaction_details)
        # TODO: check if it is needed (it shouldn't be bc data.transaction is
        # a reference to transaction)
        data["transaction"] = transaction

    return render(request, "new_transaction_detail.html", data)
