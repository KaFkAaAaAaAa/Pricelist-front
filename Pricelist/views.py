from typing import Iterable
from uuid import UUID
from django.http.response import Http404, HttpResponseForbidden
from django.http.response import HttpResponseNotFound
import requests
from django.shortcuts import render, redirect
from .forms import LoginForm, PasswordResetForm, RegisterForm, NewAdminForm
from django.core.files.storage import FileSystemStorage
import re
from django.utils.translation import gettext as _
from django.utils.translation import get_language
from math import floor
import xml.etree.ElementTree as ET

API_BASE_URL = "http://127.0.0.1:8888"

ADMIN_GROUPS = ["ADMIN", "OWNER"]

CLIENT_GROUPS = ["FIRST", "SECOND", "THIRD", "FOURTH"]

GROUPS_ROMAN = ["I", "II", "III", "IV"]

LANGS = ["PL", "EN", "DE", "FR", "IT"]

CATEGORIES = {
    "PL": [
        "Procesory",
        "Płytki",
        "Pamięci",
        "Elementy Komputera",
        "Całe urządzenia",
        "Kable i wtyczki",
        "Elementy z zawartością miedzi",
        "Metale",
    ],
    "DE": [
        "Prozessoren",
        "Platinen",
        "Speicher",
        "Computerkomponenten",
        "Ganze Geräte",
        "Kabel und Stecker",
        "Kupferhaltige Elemente",
        "Metalle",
    ],
    "EN": [
        "Processors",
        "Boards",
        "Memory",
        "Computer Components",
        "Complete Devices",
        "Cables and Plugs",
        "Copper Components",
        "Metals",
    ],
    "FR": [
        "Processeurs",
        "Carrelage",
        "En mémoire",
        "Composants informatiques",
        "Appareils entiers",
        "Câbles et prises",
        "Éléments contenant du cuivre",
        "Metaux",
    ],
    "IT": [
        "Processori",
        "Piastrelle",
        "In memoria",
        "Componenti del computer",
        "Dispositivi interi",
        "Cavi e spine",
        "Elementi contenenti rame",
        "Metalli",
    ],
}


# TODO: JSON errors -> if json error then redirect(login)


def favicon(request):
    return HttpResponseNotFound()


def _get_PLN_exr():
    with open("pln_exr.txt", "r", encoding="utf-8") as f:
        return float(f.read().rstrip().split("\t")[-1])


def _get_auth(token):
    if not token:
        return
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/auth/whoami/", headers=headers)
    try:
        if response.status_code != 200:
            return
        auth = response.json()
        auth["token"] = token
        auth["headers"] = headers
        auth["group"] = auth["group"].rstrip("]").lstrip("[")
        return auth
    except:
        return


def _list_items(item_sku, fs=FileSystemStorage()):
    """Return list of images' urls that are associated with item of id `id_sku`"""
    all_images = fs.listdir(".")[1]
    all_images.sort()
    images_sku = []
    pattern = re.compile(r"{}.*".format(item_sku))

    # TODO: can be optimized with binary search - look for any occurrence and then look for first one,
    # then while match append
    # another optimization -> after finding match if not matching break still O{n} but with low probablility
    for image in all_images:
        if re.match(pattern, image) and not re.match(r".*\.M\..*", image):
            images_sku.append(image)
    return [fs.url(image) for image in images_sku]


def _group_to_roman(group_to_translate):
    """Return (str) roman group name, by full group name, if group name invalid return null"""
    for i, group_full in enumerate(CLIENT_GROUPS):
        if group_to_translate == group_full:
            return GROUPS_ROMAN[i]
    return


# Login View
def login_view(request):

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            payload = {
                "email": form.cleaned_data["email"],
                "password": form.cleaned_data["password"],
            }
            response = requests.post(f"{API_BASE_URL}/auth/login", json=payload)
            if response.status_code == 200:
                request.session["token"] = response.json().get("token")
                response_auth = requests.get(
                    f"{API_BASE_URL}/auth/whoami/",
                    headers={"Authorization": f'Bearer {request.session["token"]}'},
                )
                request.session["logged_user"] = response_auth.json().get("currentUser")
                return redirect("price_list")
            else:
                return render(
                    request,
                    "login.html",
                    {"form": form, "error": "Invalid credentials"},
                )
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


# Logout View
def logout_view(request):
    request.session.flush()
    return redirect("login")


# Register View
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            payload = {
                "userFirstName": form.cleaned_data["userFirstName"],
                "userLastName": form.cleaned_data["userLastName"],
                "userEmail": form.cleaned_data["userEmail"],
                "userTelephoneNumber": form.cleaned_data["userTelephoneNumber"],
                "clientCompanyName": form.cleaned_data["clientCompanyName"],
                "clientStreet": form.cleaned_data["clientStreet"],
                "clientCode": form.cleaned_data["clientCode"],
                "clientCity": form.cleaned_data["clientCity"],
                "clientCountry": form.cleaned_data["clientCountry"],
            }
            response = requests.post(f"{API_BASE_URL}/auth/register", json=payload)
            if response.status_code == 200:
                return render(request, "register_success.html")
            else:
                return render(
                    request,
                    "register.html",
                    {"form": form, "error": "Registration failed."},
                )
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})


def client_panel(request):
    # TODO: add some logic
    return render(request, "client_dashboard.html")


def price_list(request):

    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if auth["group"] not in ADMIN_GROUPS and auth["group"] not in CLIENT_GROUPS:
        return HttpResponseForbidden(
            "<h1>You do not have access to that page<h1>".encode("utf-8")
        )

    lang = request.LANGUAGE_CODE.upper()
    pln_exr = False

    if lang == "PL":
        pln_exr = _get_PLN_exr()

    if "search" in request.GET.keys():
        response = requests.get(
            f"{API_BASE_URL}/items/search?lang={lang}&query={request.GET['search']}",
            headers=headers,
        )
    else:
        response = requests.get(
            f"{API_BASE_URL}/items/price-list?lang={lang}", headers=headers
        )
    items = {}
    items = (
        response.json() if response.status_code == 200 else {}
    )  # items = {<String>:<List<PricelistItemModel>>}
    for category in items.keys():
        for item in items[category]:
            # if PL add PLN
            if pln_exr:
                item["price_pln"] = floor(item["price"] * pln_exr)
                item["price_pln"] = f"{item['price_pln'] / 100:.2f}"
            item["price"] = f"{item['price'] / 100:.2f}"

    return render(
        request, "price_list.html", {"items": items, "categories": CATEGORIES[lang]}
    )


def item_detail(request, item_sku):
    if not re.match(r"^\w\w\d\d$", item_sku):
        raise Http404
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    response = requests.get(
        f"{API_BASE_URL}/items/{item_sku}?lang={request.LANGUAGE_CODE.upper()}",
        headers=headers,
    )
    if response.status_code == 200:
        item = response.json()
        images = _list_items(item_sku, FileSystemStorage())
        if request.LANGUAGE_CODE.upper() == "PL":
            pln_exr = _get_PLN_exr()
            if pln_exr:
                item["price_pln"] = floor(item["price"] * pln_exr)
                item["price_pln"] = f"{item['price_pln'] / 100:.2f}"
        item["price"] = f"{item['price'] / 100:.2f}"
        return render(request, "item_detail.html", {"item": item, "images": images})
    else:
        return render(request, "item_detail.html", {"error": "Item not found."})


def profile(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    user_admin = True

    if auth["group"] not in ADMIN_GROUPS:
        user_admin = False

    if request.method == "POST":
        err = ""
        payload = {
            "userEmail": request.POST["userEmail"],
            "userFirstName": request.POST["userFirstName"],
            "userLastName": request.POST["userLastName"],
            "userTelephoneNumber": request.POST["userTelephoneNumber"],
        }
        if not user_admin:
            client_payload = {
                "clientCompanyName": request.POST["clientCompanyName"],
                "clientStreet": request.POST["clientStreet"],
                "clientCode": request.POST["clientCode"],
                "clientCity": request.POST["clientCity"],
                "clientCountry": request.POST["clientCountry"],
            }
            client_response = requests.post(
                f"{API_BASE_URL}/clients/self/", json=client_payload, headers=headers
            )
            if client_response.status_code != 200:
                err = "500 Internal Server Error"
        response = requests.post(
            f"{API_BASE_URL}/users/self/", json=payload, headers=headers
        )
        if response.status_code != 200 and not err:
            err = "500 Internal Server Error"
        elif not err:
            msg = "User data changed successfully"
        # TODO: figure out how to redirect there correctly
        response_auth = requests.get(
            f"{API_BASE_URL}/auth/whoami/",
            headers={"Authorization": f'Bearer {request.session["token"]}'},
        )
        request.session["logged_user"] = response_auth.json().get("currentUser")

    # auth here might be problematic only in race condition situation - highly unlikely
    # although current implementation is not the most optimal and might need some clean ups
    logged = request.session["logged_user"]
    if not user_admin:
        initial = {
            "userFirstName": logged.get("user").get("userFirstName"),
            "userLastName": logged.get("user").get("userLastName"),
            "userEmail": logged.get("user").get("userEmail"),
            "userTelephoneNumber": logged.get("user").get("userTelephoneNumber"),
            "clientCompanyName": logged.get("clientCompanyName"),
            "clientStreet": logged.get("clientStreet"),
            "clientCode": logged.get("clientCode"),
            "clientCity": logged.get("clientCity"),
            "clientCountry": logged.get("clientCountry"),
        }
    else:
        initial = {
            "userFirstName": logged.get("userFirstName"),
            "userLastName": logged.get("userLastName"),
            "userEmail": logged.get("userEmail"),
            "userTelephoneNumber": logged.get("userTelephoneNumber"),
        }
    return render(
        request, "profile.html", {"initial": initial, "user_admin": user_admin}
    )


# admin views


def admin_dashboard(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    if auth.get("group") not in ADMIN_GROUPS:
        return HttpResponseForbidden(
            "<h1>You do not have access to that page<h1>".encode("utf-8")
        )

    return render(request, "admin_dashboard.html")


def admin_items(request):
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
    lang = request.LANGUAGE_CODE.upper()

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
            f"{group_price / 100:.2f}" for group_price in item["itemPrice"]
        ]
        items_dict[item.get("itemGroup")].append(item)
    return render(request, "item_list.html", {"items": items_dict})


def edit_item(request, item_sku):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if request.method == "POST":
        payload = {
            "itemSku": request.POST.get("itemSku"),
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
                int(floor(float(request.POST.get(f"itemPrice-{i}")) * 100))
                for i in range(1, 5)
            ],
        }
        if not re.match(r"^\w\w\d\d$", item_sku):
            return render(request, "edit_item.html", {"error": "Wrong sku format"})

        # not used??
        if request.POST.get("deleteImg"):
            # print(request.POST.get('deleteImg'))
            payload["itemImgPath"] = ""
        response = requests.put(
            f"{API_BASE_URL}/items/admin/{item_sku}", headers=headers, json=payload
        )
        if response.status_code == 200:
            return redirect("item_list")
        else:
            # error = payload.error
            return redirect("item_list")
    else:
        response = requests.get(
            f"{API_BASE_URL}/items/admin/{item_sku}", headers=headers
        )
        item = response.json() if response.status_code == 200 else 0
        if item:
            item["itemPrice"] = [
                f"{group_price / 100:.2f}" for group_price in item["itemPrice"]
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
        else:
            return render(request, "edit_item.html", {"error": "Item not found!"})


def delete_item(request, item_sku):
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

    response = requests.delete(
        f"{API_BASE_URL}/items/admin/{item_sku}", headers=headers
    )
    # TODO: Errors and success messages
    if response.status_code == 200:
        return redirect("item_list")
    else:
        return redirect("item_list")


def upload_image(request, item_sku):
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

    uploaded_url = None
    if request.method == "POST" and "image" in request.FILES.keys():
        image = request.FILES["image"]
        # fs = FileSystemStorage(allow_overwrite=True)
        # django needs an update to 5.1.5 so that can work
        # for now we have a workaround
        fs = FileSystemStorage()
        filename = f"{item_sku}.M.{image.name.split('.')[-1]}"
        if fs.exists(filename):
            fs.delete(filename)
        filename = fs.save(filename, image)
        # end workaround
        uploaded_url = fs.url(filename)
        response = requests.post(
            f"{API_BASE_URL}/items/admin/{item_sku}/img-path",
            headers=headers,
            data={"path": uploaded_url},
        )
        # TODO: Error handling
        if response.status_code == 200:
            redirect("edit_item", item_sku)
        else:
            redirect("edit_item", item_sku)
    return render(
        request,
        "upload_image.html",
        {"uploaded_url": uploaded_url, "item_sku": item_sku},
    )


def delete_image(request, image_path):
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

    fs = FileSystemStorage()
    image_fs = image_path.split("/")[-1]
    if fs.exists(image_fs):
        fs.delete(image_fs)
    if re.match(r".*\.M\..*", image_path):
        sku = re.match(r"\w\w\d\d(?=.*)", image_path)
        requests.post(
            f"{API_BASE_URL}/items/admin/{sku.group()}/img-path",
            headers=headers,
            data={"path": ""},
        )
    fs.delete(image_path)
    redir_url = request.headers.get("referer")
    if not redir_url:
        # error improper request
        redir_url = "item_list"
    return redirect(redir_url)


def null_delete(request):
    redir_url = request.headers.get("referer")
    if not redir_url:
        # error improper request
        redir_url = "item_list"
    return redirect(redir_url)


def admin_images(request, item_sku):
    # TODO: Upload image restrictions!!!
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    if auth.get("group") not in ADMIN_GROUPS:
        return HttpResponseForbidden(
            "<h1>You do not have access to that page<h1>".encode("utf-8")
        )

    fs = FileSystemStorage()
    images_url = _list_items(item_sku)
    if request.method == "POST" and "image" in request.FILES.keys():
        images_url = _list_items(item_sku, fs)
        # this takes .M. into the count and shouldn't but it does not break anything
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


def add_item(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    # TODO: Errors and success messages
    if request.method == "POST":
        # image = request.FILES['image']
        # fs = FileSystemStorage()
        item_sku = request.POST.get("itemSku")
        if not re.match(r"^\w\w\d\d$", item_sku):
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
        for price_group in prices:
            if price_group:
                price_group = int(100 * float(price_group))
            else:
                price_group = 0
        print(prices)
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
            "itemPrice": [int(100 * float(price)) if price else 0 for price in prices],
        }

        response = requests.post(
            f"{API_BASE_URL}/items/admin/", headers=headers, json=payload
        )
        if response.status_code == 200:
            return redirect("upload_image", item_sku)
        else:
            return render(
                request,
                "add_item.html",
                {
                    "range": range(1, 5),
                    "categories": CATEGORIES["EN"],
                    "error": "API error",
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


def new_admin(request, msg=None):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    if request.method == "POST":
        form = NewAdminForm(request.POST)
        if form.is_valid():
            payload = {
                "email": form.cleaned_data["userEmail"],
                "firstName": form.cleaned_data["userFirstName"],
                "lastName": form.cleaned_data["userLastName"],
            }
            response = requests.post(
                f"{API_BASE_URL}/auth/admin/new-admin", headers=headers, json=payload
            )
            if response.status_code == 200:
                return render(
                    request,
                    "new_admin.html",
                    {"form": form, "msg": "Admin successfully added!"},
                )
            else:
                return render(
                    request, "new_admin.html", {"form": form, "error": "Invalid email"}
                )
    else:
        form = NewAdminForm()
    return render(request, "new_admin.html", {"form": form, "msg": msg})


def my_users(request, msg="", func="activate-user"):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    response = requests.get(
        f"{API_BASE_URL}/clients/admin/admin-list/sorted?sort=unassigned",
        headers=headers,
    )
    clients = response.json()
    if response.status_code == 200 and isinstance(clients, Iterable):
        msg += " No clients found"
        return render(
            request,
            "new_users.html",
            {"clients": clients, "msg": msg, "func": func},
        )
    else:
        return render(
            request,
            "new_users.html",
            {"error": "API error!", "msg": msg, "func": func},
        )


def new_users(request, msg="", func="assign-admin"):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    response = requests.get(f"{API_BASE_URL}/clients/admin/no-admin/", headers=headers)
    clients = response.json()
    if response.status_code == 200 and isinstance(clients, Iterable):
        return render(
            request,
            "new_users.html",
            {"clients": clients, "msg": msg, "func": func},
        )
    else:
        return render(
            request,
            "new_users.html",
            {"error": "API error!", "msg": msg, "func": func},
        )


def assign_admin(request, user_id):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    user_response = requests.get(
        f"{API_BASE_URL}/users/admin/{user_id}", headers=headers
    )
    admins_response = requests.get(
        f"{API_BASE_URL}/users/admin/admins/", headers=headers
    )
    userEmail = user_response.json()["userEmail"]

    admins = {}
    try:
        admins_response = admins_response.json()
        for admin in admins_response:
            admins[
                admin["userLastName"] if admin["userLastName"] else admin["userEmail"]
            ] = admin["userId"]
    except:
        print("exception during fetching admins list from DB")

    payload = False
    if request.method == "POST":
        for name in admins.keys():
            if request.POST["admin"] == name:
                payload = {"clientAdminId": admins[name]}
                break
        if not payload:
            pass
        response = requests.put(
            f"{API_BASE_URL}/clients/admin/{user_id}",
            json=payload,
            headers=headers,
        )
        if response.status_code == 200:
            return redirect("new_users")
        else:
            return render(
                request,
                "assign_admin.html",
                {"email": userEmail, "error": "API error!"},
            )
    return render(
        request, "assign_admin.html", {"email": userEmail, "admins": admins.keys()}
    )


def activate_user(request, user_id):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    response = requests.get(f"{API_BASE_URL}/users/admin/{user_id}", headers=headers)
    userEmail = response.json()["userEmail"]
    response_group = requests.get(
        f"{API_BASE_URL}/auth/admin/{user_id}/group", headers=headers
    )
    user_group = response_group.json()["group"]

    if request.method == "POST":
        group = request.POST["group"]
        index = GROUPS_ROMAN.index(group)
        group = CLIENT_GROUPS[index]
        response = requests.get(
            f"{API_BASE_URL}/auth/admin/new-users/activate/{user_id}?group={group}",
            headers=headers,
        )
        if response.status_code == 200:
            return redirect("my_users")
        else:
            return render(
                request,
                "activate_user.html",
                {"email": userEmail, "error": "API error!"},
            )
    return render(
        request,
        "activate_user.html",
        {
            "email": userEmail,
            "groups": GROUPS_ROMAN,
            "user_group": _group_to_roman(user_group),
        },
    )


def client_list(request):
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

    response = requests.get(f"{API_BASE_URL}/clients/admin/", headers=headers)
    try:
        clients = response.json() if response.status_code == 200 else []
    except:
        clients = []
    return render(request, "client_list.html", {"clients": clients})


def client_detail(request, client_id):
    if not isinstance(client_id, UUID):
        raise Http404
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
        f"{API_BASE_URL}/clients/admin/{client_id}", headers=headers
    )
    if response.status_code == 200:
        client = response.json()
        return render(request, "client_detail.html", {"client": client})
    else:
        return render(request, "client_detail.html", {"error": "Item not found."})


def client_delete(request, client_id):
    if not isinstance(client_id, UUID):
        raise Http404
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

    response = requests.delete(
        f"{API_BASE_URL}/clients/admin/{client_id}", headers=headers
    )
    # TODO: Errors and success messages
    if response.status_code == 200:
        return redirect("client_list")
    else:
        return redirect("client_list")


def client_add(request):
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
        form = RegisterForm(request.POST)
        if form.is_valid():
            payload = {
                "userFirstName": form.cleaned_data["userFirstName"],
                "userLastName": form.cleaned_data["userLastName"],
                "userEmail": form.cleaned_data["userEmail"],
                "userTelephoneNumber": form.cleaned_data["userTelephoneNumber"],
                "clientCompanyName": form.cleaned_data["clientCompanyName"],
                "clientStreet": form.cleaned_data["clientStreet"],
                "clientCode": form.cleaned_data["clientCode"],
                "clientCity": form.cleaned_data["clientCity"],
                "clientCountry": form.cleaned_data["clientCountry"],
            }
            response = requests.post(f"{API_BASE_URL}/auth/register", json=payload)
            if response.status_code == 200:
                return redirect("client_list")
            return render(
                request,
                "new_client.html",
                {"form": form, "error": "Adding new user failed."},
            )
    else:
        form = RegisterForm()
    return render(request, "new_client.html", {"form": form})


def edit_client(request, client_id):
    token = request.session.get("token")
    auth = _get_auth(token)
    error = ""
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")

    if auth.get("group") not in ADMIN_GROUPS:
        return HttpResponseForbidden(
            "<h1>You do not have access to that page<h1>".encode("utf-8")
        )

    if request.method == "POST":
        payload_user = {
            "userLastName": request.POST["userLastName"],
            "userFirstName": request.POST["userFirstName"],
            "userEmail": request.POST["userEmail"],
            "userTelephoneNumber": request.POST["userTelephoneNumber"],
        }

        payload_client = {
            "clientCompanyName": request.POST["clientCompanyName"],
            "clientStreet": request.POST["clientStreet"],
            "clientCode": request.POST["clientCode"],
            "clientCity": request.POST["clientCity"],
            "clientCountry": request.POST["clientCountry"],
        }

        response_user = requests.put(
            f"{API_BASE_URL}/users/admin/{client_id}", json=payload_user
        )
        response_client = requests.put(
            f"{API_BASE_URL}/clients/admin/{client_id}", json=payload_client
        )
        if response_user.status_code == 200 and response_client.status_code == 200:
            render(request, "edit_client.html", {"error": error})

    client = requests.get(f"{API_BASE_URL}/clients/admin/{client_id}").json()
    return render(request, "edit_client.html", {"client": client})


def change_password(request):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]
    form = PasswordResetForm()
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            payload = {
                "password": form.cleaned_data["password"],
                "confirmPassword": form.cleaned_data["confirmPassword"],
            }
            response = requests.post(
                f"{API_BASE_URL}/auth/change-password", headers=headers, json=payload
            )
            if response.status_code == 200:
                try:
                    return redirect("/", {"msg": "Password changed successfully!"})
                except:
                    return redirect("/")
        return render(
            request,
            "change_password.html",
            {"form": form, "err": "Passwords doesn't match!"},
        )
    return render(request, "change_password.html", {"form": form})
