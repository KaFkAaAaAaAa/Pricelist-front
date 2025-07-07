import copy
import logging
import os
import re
from collections import defaultdict
from datetime import date, datetime
from http.client import INTERNAL_SERVER_ERROR, NOT_FOUND, UNAUTHORIZED
from math import floor
from pathlib import Path
from typing import Iterable, Literal

import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import (FileResponse, HttpResponse, HttpResponseNotFound,
                         HttpResponseServerError)
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from file_manager.views import _sanitize_path
from items.views import _add_items_to_offer, _make_price_list
from pdfgenerator.views import generate_pdf
from Pricelist.settings import (ADMIN_GROUPS, API_BASE_URL, BASE_DIR,
                                CLIENT_GROUPS, MAX_FILE_SIZE, SKU_REGEX,
                                SUPPORT_GROUPS, TRANSACTION_FINAL,
                                TRANSACTION_ROOT)
from Pricelist.utils import (ItemOrdered, Page, _amount_to_display,
                             _amount_to_float, _amount_to_store,
                             _api_error_interpreter, _file_indexer, _get_group,
                             _get_headers, _get_page_param, _is_admin,
                             _make_api_request, _price_to_display,
                             _price_to_float, _price_to_store, require_auth,
                             require_group)
from transactions.forms import STATUSES, ItemForm, PrognoseFrom, StatusForm

logger = logging.getLogger(__name__)


def _generate_doc_filename(transaction, status=None):
    """generates a file name for a transaction with keys client, status and status time"""
    try:
        transaction["init_time"] = _get_date_from_datetime(transaction["init_time"])
        status_name = status if status else transaction["status"]
        if "client" in transaction.keys():
            client = transaction["client"]["clientCompanyName"]
        else:
            client = transaction["clientName"]
        return f'{transaction["init_time"]}_{client}_{status_name}.pdf'
    except KeyError:
        logger.error("Key error in func _generate_doc_filename: %s", transaction)
        return "document_name_error"


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
        # TODO: bug, after changing the laguage, the values are stored in string
        for possible_int in (item[key_p], item[key_a]):
            if not isinstance(possible_int, int):
                return {"mass": 0, "price": 0}
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


def _parse_date(date_to_parse: str) -> datetime:
    return datetime.fromisoformat(date_to_parse)


def _get_date_from_datetime(date_to_parse: datetime) -> date:
    return date_to_parse.date()


def _parse_transaction_edit_items(request):
    """function parses post parameters in format {field}-{item-uuid}
    returns item list and alku dictionary {"uuid": value}"""
    items = {}
    alku = {}
    for param in request.POST:
        if param.find("-") == -1 or param in ("client-name", "client-address"):
            continue
        field, uuid = param.split("-", 1)
        if not (field and uuid):
            continue
        if uuid not in items:
            if re.match(r"new.*", uuid) or re.match(SKU_REGEX, uuid):
                items[uuid] = {}
            else:
                items[uuid] = {"uuid": uuid}
        value = request.POST[param]
        if field == "amount":
            value = _amount_to_store(value)
        if field == "price":
            value = _price_to_store(value)
        if field == "alku":
            if re.match(r"^new.*", uuid):
                alku[items[uuid]["sku"]] = _amount_to_store(value)
            else:
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
        transaction["init_time"] = _parse_date(transaction["statusHistory"][0]["time"])
    else:
        transaction["status"] = "none"
        transaction["status_time"] = "none"
        transaction["init_time"] = "none"
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


def _add_items_to_session(request):
    request.session["current_offer"], _ = _parse_transaction_edit_items(request)


def _send_proposition_to_api(request):
    items, _ = _parse_transaction_edit_items(request)
    payload = {
        "description": request.POST["transaction_description"],
        "itemsOrdered": items,
    }
    # items already converted to "store" values
    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/",
        method=requests.post,
        headers=_get_headers(request),
        body=payload,
    )
    if error:
        return error
    if transaction:
        request.session["current_offer"] = []
        request.session.modified = True
        return redirect("client_transaction_detail", transaction["uuid"])
    return _api_error_interpreter(INTERNAL_SERVER_ERROR)


def _send_offer_to_api_admin(
    request, client_auths, current_offer, totals, client_company_names
):
    headers = _get_headers(request)
    client_uuid = None
    if request.POST["client"] != "null":
        for client in Page(client_auths["clients"]).content:
            if client["clientCompanyName"] == request.POST["client"]:
                client_uuid = client["id"]
    payload = {
        "description": request.POST["transaction_description"],
        "itemsOrdered": _current_offer_to_payload(request.session["current_offer"]),
        "clientId": client_uuid,
    }
    if not client_uuid:
        payload["clientName"] = request.POST["client-name"]
        payload["clientAddress"] = request.POST["client-address"]
    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/admin/",
        method=requests.post,
        headers=headers,
        body=payload,
    )
    if error or not transaction:
        messages.error(request, "Internal server error")
        return render(
            request,
            "offer.html",
            {
                "offer": current_offer,
                "totals": totals,
                "clients": client_company_names,
            },
        )
    request.session["current_offer"] = []
    request.session.modified = True
    return redirect("admin_transaction_detail", transaction["uuid"])


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def offer(request):
    if "current_offer" not in request.session.keys():
        request.session["current_offer"] = []

    if request.method == "POST":
        _add_items_to_session(request)

        if not _is_admin(request):
            return _send_proposition_to_api(request)
            # TODO: weird bug, after getting error from api the
            # prices aren't formatted well

    current_offer = request.session.get("current_offer")
    totals = _get_stored_item_list_to_display(current_offer)
    client_company_names = []

    if _is_admin(request):
        client_auths, error = _make_api_request(
            f"{API_BASE_URL}/clients/admin/admin-list/groups/?pageSize=200",
            headers=_get_headers(request),
        )
        if error or not client_auths:
            messages.error(request, _("Could not fetch any clients"))

        for client, client_auth in zip(
            Page(client_auths["clients"]).content, client_auths["auths"]
        ):
            if client_auth["authGroup"] in CLIENT_GROUPS:
                # TODO: two clients same company
                client_company_names.append(client["clientCompanyName"])

        if request.method == "POST":
            return _send_offer_to_api_admin(
                request, client_auths, current_offer, totals, client_company_names
            )

    return render(
        request,
        "offer.html",
        {"offer": current_offer, "totals": totals, "clients": client_company_names},
    )


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def offer_list(request):
    headers = _get_headers(request)
    if request.method == "POST":
        return _add_items_to_offer(request, headers)
    return _make_price_list(request, headers, pattern="offer_list.html")


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def delete_from_offer(request, item_sku):

    item_skus = [item.get("sku") for item in request.session["current_offer"]]
    index = item_skus.index(item_sku)
    if index is not None:
        request.session["current_offer"].pop(index)
        request.session.modified = True
    return redirect("offer")


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def add_new_item_to_transaction(request, transaction_uuid):

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
            admin_url = "admin/" if _is_admin(request) else ""
            response = requests.post(
                f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/add-item/",
                headers=_get_headers(request),
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


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def edit_item_offer(request, item_sku):
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


@require_auth
@require_group(CLIENT_GROUPS)
def client_transactions(request):
    # this is nearly the same func as the one below
    headers = _get_headers(request)

    page = _get_page_param(request)
    url = f"{API_BASE_URL}/transactions/{page}"

    transactions, error = _make_api_request(url, headers=headers)

    if error or not transactions:
        return error

    page = Page(transactions)

    for transaction in page.content:
        _set_status(transaction)
        if "itemsOrdered" in transaction.keys():
            if transaction["status"] in TRANSACTION_FINAL:
                transaction_details, error = _make_api_request(
                    f"{API_BASE_URL}/transaction-details/{transaction['uuid']}/",
                    headers=headers,
                )
                if error or not transaction_details:
                    return error
                for item in transaction["itemsOrdered"]:
                    item["amount"] = transaction_details["alkuAmount"][item["uuid"]]
            transaction["totals"] = _get_stored_item_list_to_display(
                transaction["itemsOrdered"]
            )
        else:
            transaction["totals"] = {
                "mass": 0,
                "price": 0,
            }

    return render(
        request,
        "transaction_list.html",
        {"page": page, "statuses": ["PROPOSITION", "OFFER"]},
    )


@require_auth
@require_group(ADMIN_GROUPS)
def admin_transactions(request):
    headers = _get_headers(request)

    page = _get_page_param(request)
    query = ""
    if "search" in request.GET.keys():
        query = "query=" + request.GET["search"]
    endpoint = "search" if query else ""

    url = f"{API_BASE_URL}/transactions/admin/{endpoint}{page}{'&' if page else '?'}{query}"
    transactions, error = _make_api_request(url, headers=headers)
    if error:
        return error
    page = Page(transactions)

    for transaction in page.content:
        _set_status(transaction)
        if "itemsOrdered" in transaction.keys():
            if transaction["status"] in TRANSACTION_FINAL:
                transaction_details, error = _make_api_request(
                    f"{API_BASE_URL}/transaction-details/admin/{transaction['uuid']}/",
                    headers=headers,
                )
                if error or not transaction_details:
                    return error
                for item in transaction["itemsOrdered"]:
                    item["amount"] = transaction_details["alkuAmount"][item["uuid"]]
            transaction["totals"] = _get_stored_item_list_to_display(
                transaction["itemsOrdered"]
            )
        else:
            transaction["totals"] = {
                "mass": 0,
                "price": 0,
            }

    page = Page(transactions)
    return render(
        request,
        "transaction_list.html",
        {"page": page, "statuses": ["PROPOSITION", "OFFER"]},
    )


@require_auth
@require_group(ADMIN_GROUPS)
def admin_client_transactions(request, user_id):

    response = requests.get(
        f"{API_BASE_URL}/transactions/admin/client/{user_id}/",
        headers=_get_headers(request),
    )
    transactions = response.json()
    page = Page(transactions)
    for transaction in page.content:
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

    page = Page(transactions)

    return render(
        request,
        "transaction_list.html",
        {"page": page, "statuses": ["PROPOSITION", "OFFER"]},
    )


def support_transaction_detail(request, transaction_uuid):
    headers = _get_headers(request)
    group = _get_group(request)

    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/admin/{transaction_uuid}", headers=headers
    )
    if error:
        return error

    transaction_details, error = _make_api_request(
        f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}", headers=headers
    )
    if error:
        return error

    data = {"transaction": transaction, "transaction_details": transaction_details}
    return render(request, data)


# @require_auth
# @require_group(ADMIN_GROUPS + SUPPORT_GROUPS)
# def admin_transaction_detail(request, transaction_uuid):
#     headers = _get_headers(request)
#     lang = request.LANGUAGE_CODE.upper()
#     # if auth.get("group") not in ADMIN_GROUPS:
#     #     return HttpResponseForbidden(
#     #         "<h1>You do not have access to that page<h1>".encode("utf-8")
#     #     )
#
#     msg = {}
#
#     is_logistics = request.session["group"] != "LOGISTICS"
#
#     if request.session["group"] in SUPPORT_GROUPS:
#         if not is_logistics:
#             return support_transaction_detail(request, transaction_uuid)
#
#     if request.method == "POST":
#         transaction, error = _make_api_request(
#             f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/?lang={lang}",
#             headers=headers,
#         )
#         if error or not transaction:
#             return error
#
#         if not (is_logistics and transaction["status"] in TRANSACTION_FINAL[0:1]):
#             return _api_error_interpreter(401)
#         payload = {}
#         response = requests.post(
#             f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/",
#             headers=headers,
#             json=payload,
#         )
#         if response.status_code != 200:
#             msg["err"] = "Error! Something went wrong"
#         else:
#             msg["suc"] = "transaction data changed successfully"
#
#     response = requests.get(
#         f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/?lang={lang}",
#         headers=headers,
#     )
#     transaction = response.json()
#     transaction = _set_status(transaction)
#     transaction["totals"] = _get_stored_item_list_to_display(
#         transaction["itemsOrdered"],
#     )
#     if transaction["status"] in ("PROGNOSE", "FINAL"):
#         response = requests.get(
#             f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
#             headers=headers,
#         )
#         error = _api_error_interpreter(response.status_code)
#         if error:
#             return error
#
#         transaction_details = response.json()
#         return render(
#             request,
#             "transaction_detail_admin.html",
#             {
#                 "transaction": transaction,
#                 "transactionDetails": transaction_details,
#                 "msg": msg,
#             },
#         )
#
#     return render(
#         request,
#         "transaction_detail_admin.html",
#         {
#             "transaction": transaction,
#             "msg": msg,
#         },
#     )


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def edit_transaction_item(request, transaction_uuid, item_uuid):
    """edit item in transaction for both admin and user, function chooses
    if it should behave as admin or client based on"""
    admin_url = "admin/" if _is_admin(request) else ""
    headers = _get_headers(request)

    lang = request.LANGUAGE_CODE.upper()

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
                headers=headers,
                json=payload,
            )
            if response.status_code == 200:
                if admin_url:
                    return redirect("admin_transaction_detail", transaction_uuid)
                return redirect("client_transaction_detail", transaction_uuid)

    response = requests.get(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/?lang={lang}",
        headers=headers,
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


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def delete_transaction_item(request, transaction_uuid, item_uuid):
    admin_url = "admin/" if _is_admin(request) else ""

    response = requests.delete(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/{item_uuid}",
        headers=_get_headers(request),
    )

    if response.status_code != 200:
        messages.warning(request, _("Internal Server Error"))

    return redirect("admin_transaction_detail", transaction_uuid)


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def print_transaciton(request, transaction_uuid):
    headers = _get_headers(request)

    admin_url = "admin/" if _is_admin(request) else ""
    lang = request.LANGUAGE_CODE.upper()

    response = requests.get(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/?lang={lang}",
        headers=headers,
    )

    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    transaction = response.json()
    totals = _get_stored_item_list_to_display(transaction.get("itemsOrdered", []))
    transaction = _set_status(transaction)

    data = {
        "transaction": transaction,
        "total": totals,
        "date": transaction["status_time"],
    }

    status = transaction["status"]

    if not _is_admin(request):
        if status == "PROPOSITION":
            messages.warning(request, _("Proposition cannot be printed"))
        if status == "FINAL_C":
            return print_final(request, data, "FINAL")
        return print_offer(request, data, "OFFER")

    if status == "OFFER":
        return print_offer(request, data)
    if status == "PROPOSITION":
        messages.warning(request, _("Proposition cannot be printed"))
        return redirect("admin_transaction_detail", transaction_uuid)
    data["transactionDetails"], error = _make_api_request(
        f"{API_BASE_URL}/transaction-details/{admin_url}{transaction_uuid}/",
        headers=headers,
    )
    if error:
        return error
    if status == "PROGNOSE":
        return print_prognose(request, data)
    if status in ("FINAL", "FINAL_C"):
        if admin_url and (
            "client" not in request.GET.keys() or request.GET["client"] != "1"
        ):
            return print_final_admin(request, data)
        return print_final(request, data)

    logger.error("Invalid status in print function!")
    return HttpResponseServerError()


def print_offer(request, data, status=""):
    return generate_pdf(
        request,
        "pdf_offer.html",
        data,
        _generate_doc_filename(data["transaction"], status),
    )


def print_prognose(request, data, status=""):
    transport = data["transactionDetails"]["transportCost"]
    total_amount = float(data["total"]["mass"])
    total_price = float(data["total"]["price"])
    data["transport"] = {}
    data["transport"]["transportPerKg"] = transport / total_amount
    data["transport"]["transportPercent"] = transport / total_price * 100
    data["total"]["wTransport"] = transport + total_price
    return generate_pdf(
        request,
        "pdf_prognose.html",
        data,
        filename=_generate_doc_filename(data["transaction"], status),
    )


def print_final(request, data, status=""):
    data["prognose_date"] = _parse_date(
        data["transaction"]["statusHistory"][-2]["time"]
    )
    data["total"]["alku"], data["total"]["alku_price"] = 0, 0
    for item in data["transaction"]["itemsOrdered"]:
        item["alku"] = _amount_to_float(
            data["transactionDetails"]["alkuAmount"][item["uuid"]]
        )
        item["total"] = item["alku"] * float(item["price"])
        data["total"]["alku"] += item["alku"]
        data["total"]["alku_price"] += item["total"]
    return generate_pdf(
        request,
        "pdf_final.html",
        data,
        filename=_generate_doc_filename(data["transaction"], status),
    )


def print_final_admin(request, data):
    data["prognose_date"] = _parse_date(
        data["transaction"]["statusHistory"][-2]["time"]
    )

    transport = data["transactionDetails"]["transportCost"]
    data["total"]["amount"], data["total"]["price"] = 0, 0
    for item in data["transaction"]["itemsOrdered"]:
        item["alku"] = _amount_to_float(
            data["transactionDetails"]["alkuAmount"][item["uuid"]]
        )
        item["total"] = item["alku"] * float(item["price"])
        data["total"]["amount"] += item["alku"]
        data["total"]["price"] += item["total"]
    data["transport"] = {}
    data["transport"]["transportPerKg"] = transport / data["total"]["amount"]
    data["transport"]["transportPercent"] = transport / data["total"]["price"] * 100
    for item in data["transaction"]["itemsOrdered"]:
        item["total_transport"] = (
            1 + data["transport"]["transportPercent"] / 100
        ) * item["total"]
        item["price_transport"] = item["total_transport"] / item["alku"]
    data["total"]["price_transport"] = transport + data["total"]["price"]
    return generate_pdf(
        request,
        "pdf_final_admin.html",
        data,
        filename=_generate_doc_filename(data["transaction"]),
    )


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def delete_transaction(request, transaction_uuid):
    headers = _get_headers(request)

    if not _is_admin(request):
        response = requests.delete(
            f"{API_BASE_URL}/transactions/{transaction_uuid}/", headers=headers
        )
    else:
        response = requests.delete(
            f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/", headers=headers
        )
    redir_url = request.headers.get("referer")
    if response.status_code != 200:
        messages.error(request, _("Error during transaction delete"))
    return redirect(redir_url)


@require_group(ADMIN_GROUPS)
def create_offer(request, data):
    uuid = data["transaction_uuid"]
    return change_status_api(request, uuid, "offer")


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
                "transportCost": int(
                    form.cleaned_data["delivery_price"]
                    if form.cleaned_data["delivery_price"]
                    else 0
                ),
                "informations": {
                    "delivery_info": form.cleaned_data["delivery_info"],
                    "delivery_date": str(form.cleaned_data["delivery_date"]),
                    "client_date": str(form.cleaned_data["client_date"]),
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
                text, error = _make_api_request(
                    f"{API_BASE_URL}/transaction-details/admin/{uuid}/",
                    method=requests.put,
                    headers=headers,
                    body=payload,
                )
                if error:
                    return error
            _, error = _make_api_request(
                f"{API_BASE_URL}/transactions/admin/{uuid}/",
                method=requests.put,
                headers=headers,
                body={"description": form.cleaned_data["description"]},
            )
            return change_status_api(request, uuid, "prognose")
    else:
        if "description" in data["transaction"].keys():
            description = data["transaction"]["description"]
        else:
            description = ""
        form = PrognoseFrom(initial={"description": description})

    return render(request, "create_prognose.html", {"form": form, "plates": plates})


def create_final(request, data, headers):
    uuid = data["transaction_uuid"]
    # lang = request.LANGUAGE_CODE.upper()
    # if request.method == "POST":
    #     items, alku = _parse_transaction_edit_items(request)
    #     response = requests.put(
    #         f"{API_BASE_URL}/transactions/admin/{uuid}/",
    #         json={"itemsOrdered": items, "description": request.POST["description"]},
    #         headers=headers,
    #     )
    # error = _api_error_interpreter(response.status_code)
    # if error:
    # return error

    alku = {item["uuid"]: _amount_to_store(item["amount"]) for item in data["items"]}
    response = requests.put(
        f"{API_BASE_URL}/transaction-details/admin/{uuid}/",
        json={"alkuAmount": alku},
        headers=headers,
    )
    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    return change_status_api(request, uuid, "final")

    response = requests.get(
        f"{API_BASE_URL}/transaction-details/admin/{uuid}/?lang={lang}",
        headers=headers,
    )
    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    data["transactionDetails"] = response.json()
    return render(request, "create_final.html", data)


@require_auth
@require_group(ADMIN_GROUPS + ["LOGISTICS"])
def change_status(request, transaction_uuid):
    headers = _get_headers(request)

    admin_url = (
        "admin/" if _is_admin(request) or _get_group(request) in ("LOGISTICS") else ""
    )
    lang = request.LANGUAGE_CODE.upper()

    response = requests.get(
        f"{API_BASE_URL}/transactions/{admin_url}{transaction_uuid}/?lang={lang}",
        headers=headers,
    )
    error = _api_error_interpreter(response.status_code)
    if error:
        return error

    transaction = response.json()
    totals = _get_stored_item_list_to_display(transaction["itemsOrdered"])
    transaction = _set_status(transaction)
    status = transaction["status"]
    if "select_status" in request.GET.keys() and request.GET["select_status"]:
        if STATUSES.index(request.GET["select_status"].upper()) < STATUSES.index(
            status
        ):
            uuid = transaction["uuid"]
            response = _make_api_request(
                f"{API_BASE_URL}/transactions/admin/{uuid}/update-status/?status={request.GET['select_status']}",
                headers=headers,
            )
            return redirect("admin_transaction_detail", uuid)

    if admin_url:
        if "clientId" in transaction.keys():
            response_client = requests.get(
                f"{API_BASE_URL}/clients/{admin_url}{transaction['clientId']}",
                headers=headers,
            )
            error = _api_error_interpreter(response_client.status_code)
            if error:
                return error
            response_client = response_client.json()
        else:
            transaction["clientId"] = None
            response_client = {}
    else:
        response_client = request.session["logged_user"]

    data = {
        "transaction": transaction,
        "items": transaction["itemsOrdered"],
        "client": response_client,
        "total": totals,
        "date": transaction["status_time"],
        "transaction_uuid": transaction_uuid,
    }

    if status == "PROPOSITION":
        return create_offer(request, data)
    if status == "OFFER":
        return create_prognose(request, data, headers)
    if status == "PROGNOSE":
        return create_final(request, data, headers)
    if status == "FINAL":
        change_status_api(request, transaction_uuid, "FINAL_C")
        return redirect("admin_transaction_detail", transaction_uuid)
    messages.error(request, _("Invalid status name"))
    return redirect("admin_transaction_detail", transaction_uuid)


def change_status_api(request, transaction_uuid, status):
    _, error = _make_api_request(
        f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/update-status/?status={status}",
        headers=_get_headers(request),
    )
    if error:
        return error
    else:
        return redirect("admin_transaction_detail", transaction_uuid)


@require_auth
@require_group(CLIENT_GROUPS)
def client_transaction_detail(request, transaction_uuid):
    lang = request.LANGUAGE_CODE.upper()
    headers = _get_headers(request)
    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/{transaction_uuid}/?lang={lang}",
        headers=headers,
    )
    if error:
        return error
    if request.method == "POST":
        pass

    transaction = _set_status(transaction)
    if "itemsOrdered" not in transaction.keys():
        transaction["itemsOrdered"] = {}
    transaction["totals"] = _get_stored_item_list_to_display(
        transaction["itemsOrdered"],
    )
    data = {"transaction": transaction}
    if transaction["status"] in ("PROGNOSE", "FINAL", "FINAL_C"):
        transaction_details, error = _make_api_request(
            f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
            headers=headers,
        )
        if error:
            return error

        if not (
            isinstance(transaction_details, dict)
            and "alkuAmount" in transaction_details.keys()
        ):
            return _api_error_interpreter(INTERNAL_SERVER_ERROR)

        if (
            transaction["status"] in ("FINAL", "FINAL_C")
            and transaction_details["alkuAmount"]
        ):
            for item in transaction["itemsOrdered"]:
                try:
                    item["alku"] = _amount_to_display(
                        transaction_details["alkuAmount"][item["uuid"]]
                    )
                except KeyError:
                    continue
        data["transactionDetails"] = transaction_details
        data["offer"] = "OFFER"
        data["proposition"] = "PROPOSITION"
    return render(request, "transaction_detail_client.html", data)


def process_alku(alku, payload_transaction, transaction):
    # 1. Build mappings from transaction data
    uuid_to_item = {}
    sku_to_items = defaultdict(list)  # Now stores full items for comparison

    for item in transaction["itemsOrdered"]:
        uuid = item["uuid"]
        sku = item.get("sku")
        uuid_to_item[uuid] = item
        if sku:
            sku_to_items[sku].append(item)

    sku_to_payload_item = {
        item["sku"]: item
        for item in payload_transaction["itemsOrdered"]
        if "sku" in item and "uuid" not in item
    }

    # 3. Process alku dictionary
    for sku_or_uuid, amount in list(alku.items()):
        if sku_or_uuid in uuid_to_item:
            continue

        if not re.match(SKU_REGEX, sku_or_uuid):
            alku.pop(sku_or_uuid)
            continue

        matching_items = sku_to_items.get(sku_or_uuid, [])

        if len(matching_items) == 1:
            alku[matching_items[0]["uuid"]] = amount
            alku.pop(sku_or_uuid)

        elif matching_items:
            payload_item = sku_to_payload_item.get(sku_or_uuid)
            if payload_item:
                for transaction_item in matching_items:
                    # if (transaction_item.get("name") == payload_item.get("name") and
                    #     transaction_item.get("price") == payload_item.get("price") and
                    #     transaction_item.get("additionalInfo") == payload_item.get("additionalInfo")):
                    if ItemOrdered(transaction_item) == ItemOrdered(payload_item):
                        alku[transaction_item["uuid"]] = amount
                        alku.pop(sku_or_uuid)
                        break
                else:
                    # No exact match found, use first available
                    alku[matching_items[0]["uuid"]] = amount
                    alku.pop(sku_or_uuid)


@require_auth
@require_group(ADMIN_GROUPS + ["LOGISTICS"])
def admin_transaction_detail(request, transaction_uuid):

    headers = _get_headers(request)
    lang = request.LANGUAGE_CODE.upper()

    if request.method == "POST":
        items, alku = _parse_transaction_edit_items(request)
        if "client_uuid" in request.POST.keys() and request.POST["client_uuid"]:
            payload_transaction = {
                "itemsOrdered": items,
                "clientId": request.POST["client_uuid"],
            }
        else:
            payload_transaction = {
                "itemsOrdered": items,
                "clientName": request.POST["client-name"],
                "clientAddress": request.POST["client-address"],
            }
        payload_transaction["description"] = request.POST["description"]
        transaction, error = _make_api_request(
            f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/",
            method=requests.put,
            headers=headers,
            body=payload_transaction,
        )
        if error:
            return error
        if "plates_list" in request.POST.keys():
            payload = {
                "informations": {
                    "delivery_date": request.POST["delivery_date"],
                    "client_date": request.POST["client_date"],
                    "delivery_info": request.POST["delivery_info"],
                },
                "transportCost": request.POST["transport"],
                "plates": request.POST["plates_list"].split(","),
            }
            _, error = _make_api_request(
                f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
                method=requests.put,
                headers=headers,
                body=payload,
            )
            if error:
                return error
        elif alku:

            process_alku(alku, payload_transaction, transaction)

            payload = {
                "alkuAmount": alku,
                "informations": {
                    "delivery_date": request.POST["delivery_date"],
                    "client_date": request.POST["client_date"],
                },
            }
            _, error = _make_api_request(
                f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
                method=requests.put,
                headers=headers,
                body=payload,
            )

    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/admin/{transaction_uuid}/?lang={lang}",
        headers=headers,
    )
    if error:
        return error

    transaction = _set_status(transaction)
    if "itemsOrdered" not in transaction.keys():
        transaction["itemsOrdered"] = {}
    transaction["totals"] = _get_stored_item_list_to_display(
        transaction["itemsOrdered"],
    )
    form = StatusForm(init_status=transaction["status"])
    data = {"transaction": transaction, "form": form}
    if transaction["status"] in ("PROGNOSE", "FINAL", "FINAL_C"):
        transaction_details, error = _make_api_request(
            f"{API_BASE_URL}/transaction-details/admin/{transaction_uuid}/",
            headers=headers,
        )
        if error:
            return error

        if not (
            isinstance(transaction_details, dict)
            and "alkuAmount" in transaction_details.keys()
        ):
            return _api_error_interpreter(INTERNAL_SERVER_ERROR)

        if (
            transaction["status"] in TRANSACTION_FINAL
            and transaction_details["alkuAmount"]
        ):
            for item in transaction["itemsOrdered"]:
                try:
                    item["alku"] = _amount_to_display(
                        transaction_details["alkuAmount"][item["uuid"]]
                    )
                except KeyError:
                    continue
        data["transactionDetails"] = transaction_details

    return render(request, "transaction_detail_admin.html", data)


@require_auth
@require_group(["LOGISTICS", "DISPO"])
def prognose_list(request):
    headers = _get_headers(request)
    page = _get_page_param(request)

    prognoses, error = _make_api_request(
        f"{API_BASE_URL}/transactions/by-status?status=PROGNOSE&{page.strip('?')}",
        headers=headers,
    )
    if error or not prognoses:
        return error
    page = Page(prognoses)
    for prognose in page.content:
        prognose["init_time"] = _parse_date(prognose["init_time"])
        prognose["status_time"] = _parse_date(prognose["status_time"])

    return render(request, "transaction_status_list.html", {"page": page})


@require_auth
@require_group(["MSB"])
def msb_list(request):
    headers = _get_headers(request)
    page = _get_page_param(request)

    transactions, error = _make_api_request(
        f"{API_BASE_URL}/transactions/admin/{page}",
        headers=headers,
    )
    page = Page(transactions)
    for transaction in page.content:
        transaction_detail, error = _make_api_request(
            f"{API_BASE_URL}/transaction-details/admin/{transaction['uuid']}",
            headers=headers,
        )
        if error or not transactions:
            return error
        transaction["transport"] = transaction_detail
        transaction["total_amount"] = (
            _calculate_total_mass(transaction["itemsOrdered"]) / 10
        )

def _validate_photo_path(path):
    root_dir = Path(path).parent
    fs = FileSystemStorage(root_dir)
    path = _sanitize_path(path, file_sys=fs)
    return path


def _photo_list(transaction_uuid, item_uuid):
    item_photo_list = []

    path = Path(f"{TRANSACTION_ROOT}/{transaction_uuid}/photos/")
    path.mkdir(parents=True, exist_ok=True)
    fs = FileSystemStorage(location=str(path))
    ls_dir = fs.listdir(".")

    for file in ls_dir[1]:
        if re.match("\w\w\d\d\d?_"+str(item_uuid)+".*", file):
            item_photo_list.append(file)

    return item_photo_list

def _save_photo(root_dir, file_name, image):
    path = Path(root_dir)
    path.mkdir(parents=True, exist_ok=True)
    fs = FileSystemStorage(location=str(path))
    fs.save(file_name, image, MAX_FILE_SIZE)

def _init_photo_operation(request, transaction_uuid, item_uuid):
    # verify request valid - client is able to read that transaction item exists
    transaction, error = _make_api_request(
        f"{API_BASE_URL}/transactions/{transaction_uuid}/",
        headers=_get_headers(request),
    )
    item = None
    if error:
        return error, False
    item_uuid = str(item_uuid)
    if item_uuid not in [item["uuid"] for item in transaction["itemsOrdered"]]:
        return _api_error_interpreter(NOT_FOUND), False
    for item_ordered in transaction["itemsOrdered"]:
        if item_uuid == item_ordered["uuid"]:
            item = item_ordered
            break
    return transaction, item

@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def add_photo(request, transaction_uuid, item_uuid):
    init_data = _init_photo_operation(request, transaction_uuid, item_uuid)
    if isinstance(init_data, HttpResponse):
        return init_data
    transaction, item = init_data
    if not item:
        # this should not happen ever - lsp warning
        return _api_error_interpreter(NOT_FOUND)
    # POST
    if (request.method == "POST" and request.FILES and "image" in request.FILES.keys()):
        image = request.FILES["image"]

        root_dir = f"{TRANSACTION_ROOT}/{transaction_uuid}/photos/" 
        ext = image.name.rsplit(".")[-1]
        file_name = _file_indexer(root_dir, f"{item['sku']}_{item_uuid}.{ext}")

        _save_photo(root_dir, file_name, image)

    elif request.method == "POST":
        messages.warning(request, _("Error during file upload"))

    file_list = _photo_list(transaction_uuid, item_uuid)

    return render(request, "add_photo.html", {
        "transaction": transaction,
        "item": item,
        "file_list": file_list,
        })



@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def delete_photo(request, transaction_uuid, item_uuid, file):
    init_data = _init_photo_operation(request, transaction_uuid, item_uuid)
    if isinstance(init_data, HttpResponse):
        return init_data
    _, item = init_data
    if not item:
        return _api_error_interpreter(NOT_FOUND)
    # Validate img_path as in get photo
    img_path = f"{TRANSACTION_ROOT}/{transaction_uuid}/photos/{file}"
    path = _validate_photo_path(img_path)
    fs = FileSystemStorage(f"{TRANSACTION_ROOT}/{transaction_uuid}/photos/")
    if fs.exists(path):
        fs.delete(path)
        return redirect("add_photo", transaction_uuid, item_uuid)
    else:
        return _api_error_interpreter(NOT_FOUND)

@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def get_photo(request, transaction_uuid, item_uuid, file):
    init_data = _init_photo_operation(request, transaction_uuid, item_uuid)
    if isinstance(init_data, HttpResponse):
        return init_data
    _, item = init_data
    if not item:
        return _api_error_interpreter(NOT_FOUND)
    img_path = f"{TRANSACTION_ROOT}/{transaction_uuid}/photos/{file}" 
    fs = FileSystemStorage(f"{TRANSACTION_ROOT}/{transaction_uuid}/photos/")
    path = _validate_photo_path(img_path)

    if not fs.exists(path):
        return _api_error_interpreter(NOT_FOUND)
    content_type = 'image/jpeg'
    return FileResponse(open(path, 'rb'), content_type=content_type)
