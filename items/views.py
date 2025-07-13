import logging
import re
from datetime import datetime
from http.client import UNAUTHORIZED
from math import floor

import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.http.response import Http404, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from pdfgenerator.views import generate_pdf
from Pricelist.settings import (
    ADMIN_GROUPS,
    API_BASE_URL,
    CATEGORIES,
    CLIENT_GROUPS,
    GROUPS_ROMAN,
    SKU_REGEX,
    SUPPORT_GROUPS,
)
from Pricelist.utils import (
    _amount_to_store,
    _api_error_interpreter,
    _get_headers,
    _is_admin,
    _price_to_display,
    _price_to_store,
    require_auth,
    require_group,
)

logger = logging.getLogger(__name__)


def _get_pln_exr():
    """return PLN exchange rate from euro, from file"""
    with open("pln_exr.txt", "r", encoding="utf-8") as f:
        return float(f.read().rstrip().split("\t")[-1])


def _list_items(item_sku, fs=FileSystemStorage()):
    """Return list of images' urls that are associated with item of id `id_sku`"""
    all_images = fs.listdir(".")[1]
    all_images.sort()
    images_sku = []
    pattern = re.compile(r"{}.*".format(item_sku))

    # TODO: can be optimized with binary search - look for any occurrence
    # and then look for first one,
    # then while match append
    # another optimization -> after finding match if not matching
    # break still O{n} but with low probablility
    for image in all_images:
        if re.match(pattern, image) and not re.match(r".*\.M\..*", image):
            images_sku.append(image)
    return [fs.url(image) for image in images_sku]


def _make_price_list(request, headers, pattern="price_list.html"):
    lang = request.LANGUAGE_CODE.upper()
    pln_exr = False

    if lang == "PL":
        pln_exr = _get_pln_exr()

    params_str = f"?lang={lang}"
    for key, val in request.GET.items():
        if key == "group":
            val = int(val) - 1
            if not _is_admin(request):
                return _api_error_interpreter(UNAUTHORIZED)
        params_str += f"&{key}={val}"
    if "search" in request.GET.keys():
        url = f"{API_BASE_URL}/items/search{params_str}"
    else:
        url = f"{API_BASE_URL}/items/price-list{params_str}"

    response = requests.get(url, headers=headers)

    items = {}
    items = (
        response.json() if response.status_code == 200 else {}
    )  # items = {<String>:<List<PricelistItemModel>>}
    is_results = False
    for category in items.keys():
        for item in items[category]:
            # if PL add PLN
            if pln_exr:
                item["price_pln"] = floor(item["price"] * pln_exr)
                item["price_pln"] = _price_to_display(item["price_pln"])
            item["price"] = _price_to_display(item["price"])

            is_results = True
    if "f" in request.GET.keys() and request.GET["f"] == "json":
        return JsonResponse({"items": items})
    if "print" in request.GET.keys() or pattern == "pdf":
        date = datetime.date(datetime.now()).strftime("%m-%Y")
        return generate_pdf(
            request,
            "pdf_pricelist.html",
            {"items": items, "categories": CATEGORIES[lang]},
            f"pricelist_alku_{date}.pdf",
        )
    return render(
        request,
        pattern,
        {
            "is_results": is_results,
            "items": items,
            "categories": CATEGORIES[lang],
            "roman_groups": GROUPS_ROMAN,
        },
    )


def _add_items_to_offer(request, headers):
    """add info needed for offer form api to session, uses request post param,
    helper for price_list func"""
    items = request.POST
    for sku in items:
        if not re.match(SKU_REGEX, sku):
            # csrf and wrong requests
            continue

        response = requests.get(
            f"{API_BASE_URL}/items/{sku}?lang={request.LANGUAGE_CODE.upper()}",
            headers=headers,
        )
        # amount in POST param is a str, price is an int
        amount = _amount_to_store(items[sku])
        item = response.json()

        item_ordered = {
            "sku": item.get("sku"),
            "name": item.get("name"),
            "price": item.get("price"),
            "amount": amount,
            "additionalInfo": "",
        }
        if (
            "current_offer" in request.session.keys()
            and isinstance(request.session["current_offer"], list)
            and request.session["current_offer"]
        ):
            if item_ordered.get("sku") not in [
                item["sku"] for item in request.session["current_offer"]
            ]:
                request.session["current_offer"].append(item_ordered)
            else:
                # TODO: figure out some way to handle
                # "item is already in the offer" situation
                pass
        else:
            request.session["current_offer"] = [item_ordered]
    if (
        not request.session.get("current_offer")
        or len(request.session.get("current_offer")) == 0
    ):
        return redirect("price_list")
    request.session.modified = True
    return redirect("offer")


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS + SUPPORT_GROUPS)
def price_list(request):
    if request.session["auth"]["group"] in SUPPORT_GROUPS:
        return redirect("prognose_list")
    return _make_price_list(request, _get_headers(request))


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def price_list_print(request):
    return _make_price_list(request, _get_headers(request), pattern="pdf")


@require_auth
@require_group(ADMIN_GROUPS + CLIENT_GROUPS)
def item_detail(request, item_sku):

    if not re.match(SKU_REGEX, item_sku):
        raise Http404

    response = requests.get(
        f"{API_BASE_URL}/items/{item_sku}?lang={request.LANGUAGE_CODE.upper()}",
        headers=_get_headers(request),
    )
    if response.status_code == 200:
        item = response.json()
        images = _list_items(item_sku, FileSystemStorage())
        if request.LANGUAGE_CODE.upper() == "PL":
            pln_exr = _get_pln_exr()
            if pln_exr:
                item["price_pln"] = floor(item["price"] * pln_exr)
                item["price_pln"] = _price_to_display(item["price_pln"])
        item["price"] = _price_to_display(item["price"])
        return render(request, "item_detail.html", {"item": item, "images": images})
    return HttpResponseNotFound()


@require_auth
@require_group(ADMIN_GROUPS)
def admin_items(request):
    lang = request.LANGUAGE_CODE.upper()
    headers = _get_headers(request)

    if "search" in request.GET.keys():
        response = requests.get(
            f"{API_BASE_URL}/items/admin/search?lang={lang}&query={request.GET['search']}",
            headers=headers,
        )
    else:
        response = requests.get(f"{API_BASE_URL}/items/admin/", headers=headers)
    items = response.json() if response.status_code == 200 else []
    items_dict = {}
    for category in CATEGORIES.get("EN"):
        items_dict[category] = []
    for item in items:
        item["itemPrice"] = [
            _price_to_display(group_price) for group_price in item["itemPrice"]
        ]
        item["localized_name"] = item["itemName"][lang]
        items_dict[item.get("itemGroup")].append(item)
    return render(request, "item_list.html", {"items": items_dict})


@require_auth
@require_group(ADMIN_GROUPS)
def edit_item(request, item_sku):
    headers = _get_headers(request)

    if request.method == "POST":
        payload = {
            "itemSku": request.POST.get("itemSku"),
            "itemAccountingNumber": request.POST.get("itemAccNo"),
            "itemGroup": request.POST.get("itemGroup"),
            "itemName": {
                "DE": request.POST.get("DE-n"),
                "EN": request.POST.get("EN-n"),
                "IT": request.POST.get("IT-n"),
                "FR": request.POST.get("FR-n"),
                "PL": request.POST.get("PL-n"),
            },
            "itemDescription": {
                "DE": request.POST.get("DE-d"),
                "EN": request.POST.get("EN-d"),
                "IT": request.POST.get("IT-d"),
                "FR": request.POST.get("FR-d"),
                "PL": request.POST.get("PL-d"),
            },
            "itemPrice": [
                _price_to_store(request.POST.get(f"itemPrice-{i}")) for i in range(1, 5)
            ],
        }
        if not re.match(SKU_REGEX, item_sku):
            return render(request, "edit_item.html", {"error": "Wrong sku format"})

        # not used??
        if request.POST.get("deleteImg"):
            # print(request.POST.get('deleteImg'))
            payload["itemImgPath"] = ""
            # TODO: delete the image XD
        response = requests.put(
            f"{API_BASE_URL}/items/admin/{item_sku}",
            headers=headers,
            json=payload,
        )
        if response.status_code == 200:
            messages.success(request, _("Item edited successfully"))
            return redirect("item_list")
        if response.text == "SKU exists":
            messages.error(request, _("Error, SKU already exists"))
        else:
            messages.error(request, _("Error, item has not been edited"))
        return render(request, "edit_item.html")

    response = requests.get(f"{API_BASE_URL}/items/admin/{item_sku}", headers=headers)
    item = response.json() if response.status_code == 200 else 0
    if item:
        item["itemPrice"] = [
            _price_to_display(group_price) for group_price in item["itemPrice"]
        ]
        return render(
            request,
            "edit_item.html",
            {
                "item": item,
                "range": range(1, 5),
                "categories": CATEGORIES["EN"],
            },
        )
    return render(request, "edit_item.html", {"error": "Item not found!"})


@require_auth
@require_group(ADMIN_GROUPS)
def delete_item(request, item_sku):

    response = requests.delete(
        f"{API_BASE_URL}/items/admin/{item_sku}", headers=_get_headers(request)
    )
    if response.status_code == 200:
        messages.success(request, _("Item deleted successfully!"))
        return redirect("item_list")
    else:
        messages.error(request, _("API error"))
        return redirect("item_list")


@require_auth
@require_group(ADMIN_GROUPS)
def upload_image(request, item_sku):

    uploaded_url = None
    if request.method == "POST" and "image" in request.FILES.keys():
        image = request.FILES["image"]
        # fs = FileSystemStorage(allow_overwrite=True)
        # django needs an update to 5.1.5 so that can work
        # for now we have a workaround
        fs = FileSystemStorage()
        ext = image.name.rsplit(".")[-1]
        if ext not in ("jpg", "JPG"):
            return HttpResponseForbidden(b"Only jpg is allowed")
        filename = f"{item_sku}.M.{ext}"
        if fs.exists(filename):
            fs.delete(filename)
        filename = fs.save(filename, image)
        # end workaround
        uploaded_url = fs.url(filename)
    return render(
        request,
        "upload_image.html",
        {"uploaded_url": uploaded_url, "item_sku": item_sku},
    )


@require_auth
@require_group(ADMIN_GROUPS)
def delete_image(request, image_path):
    redir_url = request.headers.get("referer")
    fs = FileSystemStorage()
    image_fs = image_path.split("/")[-1]
    if fs.exists(image_fs):
        fs.delete(image_fs)
    if re.match(r".*\.M\..*", image_path):
        sku_regex_from_filename = SKU_REGEX.rstrip("$") + "(?.*)"
        sku = re.match(sku_regex_from_filename, image_path)
        if not sku:
            return redirect(redir_url)
        requests.post(
            f"{API_BASE_URL}/items/admin/{sku.group()}/img-path",
            headers=_get_headers(request),
            data={"path": ""},
        )
    fs.delete(image_path)
    if not redir_url:
        # error improper request
        redir_url = "item_list"
    return redirect(redir_url)


@require_auth
@require_group(ADMIN_GROUPS)
def null_delete(request):
    redir_url = request.headers.get("referer")
    if not redir_url:
        # error improper request
        redir_url = "item_list"
    return redirect(redir_url)


@require_auth
@require_group(ADMIN_GROUPS)
def admin_images(request, item_sku):
    # TODO: Upload image restrictions!!!
    fs = FileSystemStorage()
    images_url = _list_items(item_sku)
    if request.method == "POST" and "image" in request.FILES.keys():
        images_url = _list_items(item_sku, fs)
        # this takes .M. into the count and shouldn't but it does not
        # break anything
        index = len(images_url) if len(images_url) != 1 else 0
        images_uploaded = request.FILES.getlist("image")
        # TODO: optimize - binary search
        image_name = item_sku + "." + images_uploaded[0].name.split(".")[-1]
        if not index and not fs.exists(image_name):
            fs.save(image_name, images_uploaded[0])
            images_uploaded.pop(0)
            index = 1
        for image in images_uploaded:
            index += 1
            # sku + index + extension
            image_name = item_sku + "." + str(index) + "." + image.name.split(".")[-1]
            if not fs.exists(image_name):
                fs.save(image_name, image)
            else:
                while fs.exists(image_name):
                    index += 1
                image_name = (
                    item_sku + "." + str(index) + "." + image.name.split(".")[-1]
                )
                fs.save(image_name, image)

        return redirect("admin_images", item_sku)
    return render(
        request, "admin_images.html", {"images": images_url, "item_sku": item_sku}
    )


@require_auth
@require_group(ADMIN_GROUPS)
def add_item(request):
    headers = _get_headers(request)
    if request.method == "POST":
        # image = request.FILES['image']
        # fs = FileSystemStorage()
        item_sku = request.POST.get("itemSku")
        if not re.match(SKU_REGEX, item_sku):
            return render(
                request,
                "add_item.html",
                {
                    "range": range(1, 5),
                    "categories": CATEGORIES["EN"],
                    "error": "Wrong sku format",
                },
            )

        # filename = fs.save(f"{item_sku}_{image.name}", image)
        # uploaded_url = fs.url(filename)
        prices = [request.POST.get(f"itemPrice-{i}") for i in range(1, 5)]
        payload = {
            "itemSku": item_sku,
            "itemGroup": request.POST.get("itemGroup"),
            "itemName": {
                "DE": request.POST.get("DE-n"),
                "EN": request.POST.get("EN-n"),
                "IT": request.POST.get("IT-n"),
                "FR": request.POST.get("FR-n"),
                "PL": request.POST.get("PL-n"),
            },
            "itemDescription": {
                "DE": request.POST.get("DE-d"),
                "EN": request.POST.get("EN-d"),
                "IT": request.POST.get("IT-d"),
                "FR": request.POST.get("FR-d"),
                "PL": request.POST.get("PL-d"),
            },
            "itemPrice": [_price_to_store(price) if price else 0 for price in prices],
        }

        response = requests.post(
            f"{API_BASE_URL}/items/admin/", headers=headers, json=payload
        )
        if response.status_code == 200:
            messages.success(request, "_(Item successfully added)")
            return redirect("upload_image", item_sku)
        if response.text == "SKU exists":
            error = _("Error, SKU already exists")
        else:
            error = _("API error")
        return render(
            request,
            "add_item.html",
            {
                "range": range(1, 5),
                "categories": CATEGORIES["EN"],
                "error": error,
            },
        )
    else:
        return render(
            request,
            "add_item.html",
            {
                "range": range(1, 5),
                "categories": CATEGORIES["EN"],
            },
        )
