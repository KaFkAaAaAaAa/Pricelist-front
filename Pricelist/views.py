import logging
import re
import urllib.parse
from asyncio import timeout
from http.client import NOT_FOUND
from typing import Iterable
from uuid import UUID

import requests
from django.contrib import messages
from django.http.response import HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from transactions.views import _set_status

from .forms import LoginForm, NewUserForm, PasswordResetForm, RegisterForm
from .settings import ADMIN_GROUPS, API_BASE_URL, CLIENT_GROUPS, GROUPS_ROMAN
from .utils import (
    Page,
    _api_error_interpreter,
    _get_headers,
    _get_page_param,
    _group_to_roman,
    _make_api_request,
    require_auth,
    require_group,
)

# TODO: JSON errors -> if json error then redirect(login)

logger = logging.getLogger(__name__)


def favicon():
    """render 404 for favicon request"""
    return HttpResponseNotFound()


# Login View
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            payload = {
                "email": form.cleaned_data["email"],
                "password": form.cleaned_data["password"],
            }
            try:
                response = requests.post(
                    f"{API_BASE_URL}/auth/login", json=payload, timeout=10
                )
            except ConnectionRefusedError:
                logger.error("Connection error, API is unreachable")
                return HttpResponseServerError(
                    _("Internal server error").encode("utf-8")
                )

            if response.status_code == 200:
                request.session["token"] = response.json().get("token")
                response_auth = requests.get(
                    f"{API_BASE_URL}/auth/whoami/",
                    headers={"Authorization": f'Bearer {request.session["token"]}'},
                )
                request.session["logged_user"] = response_auth.json().get("currentUser")
                if response_auth.json()["group"].strip("[]") in ["LOGISTICS"]:
                    return redirect("prognose_list")
                return redirect("price_list")
            logger.warning("Invalid credentials for email: %s", payload["email"])
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
    """logout"""
    request.session.flush()
    return redirect("login")


# Register View
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        error = ""
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
            if (
                response.status_code == 200
                and response.text == "Registration Successfull"
            ):
                return render(request, "register_success.html")
            if response.text == "Email used":
                error = _("Email is already used")
        if not error:
            error = _("Registration failed.")
        return render(
            request,
            "register.html",
            {"form": form, "error": error},
        )
    form = RegisterForm()
    return render(request, "register.html", {"form": form})


@require_auth
def client_panel(request):
    # TODO: add some logic
    return render(request, "client_dashboard.html")


@require_auth
def profile(request):

    user_admin = False
    headers = _get_headers(request)

    if request.session["auth"]["group"] in ADMIN_GROUPS:
        user_admin = True

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
                messages.error(
                    request, _("Internal server error, user data didn't change")
                )
        response = requests.post(
            f"{API_BASE_URL}/users/self/", json=payload, headers=headers
        )
        if response.status_code != 200 and not err:
            messages.error(request, _("Internal server error, user data didn't change"))
        elif not err:
            messages.success(request, _("User data changed successfully"))
        response_auth = requests.get(
            f"{API_BASE_URL}/auth/whoami/",
            headers={"Authorization": f'Bearer {request.session["token"]}'},
        )
        request.session["logged_user"] = response_auth.json().get("currentUser")

    # get_auth here might be problematic only in race condition
    # situation - highly unlikely although current implementation is not
    # the most optimal and might need some clean ups
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


@require_auth
@require_group(ADMIN_GROUPS)
def admin_dashboard(request):

    transactions, error = _make_api_request(
        f"{API_BASE_URL}/transactions/admin/?pageNo=0&pageSize=30"
    )

    users_page = None
    transactions_page = None
    if error or not transactions:
        messages.error(request, _("Error! Could not fetch transactions"))
    else:
        for transaction in transactions["content"]:
            transaction = _set_status(transaction)
        transactions_page = Page(transactions)

    users, error = _make_api_request(
        f"{API_BASE_URL}/users/admin/by-group/?group=UNASSIGNED?&pageNo=0&pageSize=30"
    )
    if error or not users:
        messages.error(request, _("Error! Could not fetch users"))
    else:
        users_page = Page(users)

    return render(
        request,
        "admin_dashboard.html",
        {"users_page": users_page, "transactions_page": transactions_page},
    )


@require_auth
@require_group(ADMIN_GROUPS)
def new_admin(request, msg=None):

    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            payload = {
                "email": form.cleaned_data["userEmail"],
                "firstName": form.cleaned_data["userFirstName"],
                "lastName": form.cleaned_data["userLastName"],
                "group": form.cleaned_data["userGroup"],
            }
            headers = _get_headers(request)
            response = requests.post(
                f"{API_BASE_URL}/auth/admin/new-admin", headers=headers, json=payload
            )
            if response.status_code == 200:
                return render(
                    request,
                    "new_admin.html",
                    {"form": form, "msg": "Admin successfully added!"},
                )
            return render(
                request, "new_admin.html", {"form": form, "error": "Invalid email"}
            )
    else:
        form = NewUserForm()
    return render(request, "new_admin.html", {"form": form, "msg": msg})


def verify_registration(request):
    __import__("pdb").set_trace()
    if request.method == "POST":
        payload = {
            "password": request.POST["password"],
            "confirmPassword": request.POST["confirmPassword"],
        }
        response, error = _make_api_request(
            f"{API_BASE_URL}/auth/reset-password/reset?token={request.GET['token']}",
            method=requests.post,
            body=payload,
        )
        if isinstance(response, str) and re.match(".*uccess.*", response):
            messages.success(request, _("Password change successful"))
        elif error:
            messages.error(request, _("API error"))
        else:
            messages.warning(request, _("Passwords are invalid"))
        redirect("login")
    return render(request, "verify_registration.html")


@require_auth
@require_group(ADMIN_GROUPS)
def my_users(request, func="activate-user"):

    page = _get_page_param(request)
    headers = _get_headers(request)
    if "search" in request.GET.keys():
        page = _get_page_param(request, False)
        search_param = "?cname=" + request.GET["search"]
        url = f"{API_BASE_URL}/clients/admin/admin-list/with-groups/search{search_param}{page}"
    else:
        page = _get_page_param(request)
        url = f"{API_BASE_URL}/clients/admin/admin-list/with-groups/{page}"
    clients, error = _make_api_request(url, headers=headers)
    if error or not clients:
        return error
    page = Page(clients)

    if page.total_elements == 0:
        messages.warning(request, _("No clients found"))

    return render(
        request,
        "new_users.html",
        {"page": page, "func": func},
    )


@require_auth
@require_group(ADMIN_GROUPS)
def new_users(request, func="assign-admin"):

    page = _get_page_param(request)
    clients, error = _make_api_request(
        f"{API_BASE_URL}/clients/admin/no-admin/{page}", headers=_get_headers(request)
    )
    if error or not clients:
        return error
    page = Page(clients)
    return render(
        request,
        "new_users.html",
        {"page": page, "func": func},
    )


@require_auth
@require_group(ADMIN_GROUPS)
def assign_admin(request, user_id):
    headers = _get_headers(request)
    user_response = requests.get(
        f"{API_BASE_URL}/users/admin/{user_id}", headers=headers
    )
    admins_response = requests.get(
        f"{API_BASE_URL}/users/admin/admins/", headers=headers
    )
    user_email = user_response.json()["userEmail"]

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
        for admin_name, admin_uuid in admins.items():
            if request.POST["admin"] == admin_name:
                payload = {"clientAdminId": admin_uuid}
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
        return render(
            request,
            "assign_admin.html",
            {"email": user_email, "error": _("API error!")},
        )
    return render(
        request, "assign_admin.html", {"email": user_email, "admins": admins.keys()}
    )


@require_auth
@require_group(ADMIN_GROUPS)
def activate_user(request, user_id):
    headers = _get_headers(request)

    response = requests.get(f"{API_BASE_URL}/users/admin/{user_id}", headers=headers)
    user_email = response.json()["userEmail"]
    response_group = requests.get(
        f"{API_BASE_URL}/auth/admin/{user_id}/group", headers=headers
    )
    user_group = response_group.json()["group"]
    if user_group in CLIENT_GROUPS:
        user_group = _group_to_roman(user_group)
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
        return render(
            request,
            "activate_user.html",
            {"email": user_email, "error": _("API error!")},
        )
    return render(
        request,
        "activate_user.html",
        {
            "email": user_email,
            "groups": GROUPS_ROMAN,
            "user_group": user_group,
        },
    )


@require_auth
@require_group(ADMIN_GROUPS)
def client_list(request):
    headers = _get_headers(request)

    if "search" in request.GET.keys():
        page = _get_page_param(request, False)
        search_param = "?cname=" + request.GET["search"]
        url = f"{API_BASE_URL}/clients/admin/with-groups/search{search_param}{page}"
    else:
        page = _get_page_param(request)
        url = f"{API_BASE_URL}/clients/admin/with-groups/{page}"
    clients, error = _make_api_request(url, headers=headers)
    if error or not clients:
        return error
    page = Page(clients)

    return render(request, "client_list.html", {"page": page})


@require_auth
@require_group(ADMIN_GROUPS)
def client_detail(request, client_id):
    if not isinstance(client_id, UUID):
        return HttpResponseNotFound(_("User not found").encode("UTF-8"))

    response = requests.get(
        f"{API_BASE_URL}/clients/admin/{client_id}", headers=_get_headers(request)
    )
    if response.status_code == 200:
        client = response.json()
        return render(request, "client_detail.html", {"client": client})
    return render(request, "client_detail.html", {"error": _("Client not found.")})


@require_auth
@require_group(ADMIN_GROUPS)
def client_delete(request, client_id):
    if not isinstance(client_id, UUID):
        return HttpResponseNotFound(_("User not found").encode("UTF-8"))

    response = requests.delete(
        f"{API_BASE_URL}/clients/admin/{client_id}", headers=_get_headers(request)
    )
    # TODO: Errors and success messages
    if response.status_code == 200:
        messages.success(request, _("Client deleted successfully"))
        return redirect("client_list")
    messages.error(request, _("Internal server error"))
    return redirect("client_list")


@require_auth
@require_group(ADMIN_GROUPS)
def client_add(request):
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
            response = requests.post(
                f"{API_BASE_URL}/auth/register?as=admin",
                json=payload,
                headers=_get_headers(request),
            )
            if response.status_code == 200:
                return redirect("new_users")
            return render(
                request,
                "new_client.html",
                {"form": form, "error": "Adding new user failed."},
            )
    else:
        form = RegisterForm()
        for bound_field in form.visible_fields():
            # TODO: fix translation here
            if "placeholder" in bound_field.field.widget.attrs:
                bound_field.field.widget.attrs["placeholder"] = (
                    bound_field.field.widget.attrs["placeholder"].replace(
                        _("your "), ""
                    )
                )
    return render(request, "new_client.html", {"form": form})


@require_auth
@require_group(ADMIN_GROUPS)
def edit_client(request, client_id):
    headers = _get_headers(request)
    last_name_to_id = {}
    admins, error = _make_api_request(
        f"{API_BASE_URL}/users/admin/admins/", headers=headers
    )
    if error:
        return error
    if not admins:
        return _api_error_interpreter(NOT_FOUND)
    for admin in admins:
        last_name_to_id[admin["userLastName"]] = admin["userId"]
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
            "clientAdminId": last_name_to_id[request.POST["clientAdminLastName"]],
        }

        response_user = requests.put(
            f"{API_BASE_URL}/users/admin/{client_id}",
            json=payload_user,
            headers=headers,
        )
        response_client = requests.put(
            f"{API_BASE_URL}/clients/admin/{client_id}",
            json=payload_client,
            headers=headers,
        )
        if response_user.status_code == 200 and response_client.status_code == 200:
            messages.success(request, _("Client edited successfully"))
            return redirect("edit_client", client_id)
        messages.error(request, _("Internal server error!"))

    client, error = _make_api_request(
        f"{API_BASE_URL}/clients/admin/{client_id}", headers=headers
    )
    if error:
        return error

    return render(request, "edit_client.html", {"client": client, "admins": admins})


@require_auth
def change_password(request):
    headers = _get_headers(request)

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
            if response.status_code == 200 and re.match(".*uccess.*", response.text):
                messages.info(request, _("Password change successful!"))
                return redirect("/profile/")
        messages.error(request, _("Passwords are invalid"))
        return render(
            request,
            "change_password.html",
            {"form": form},
        )
    return render(request, "change_password.html", {"form": form})


def reset_password(request):
    __import__("pdb").set_trace()
    if request.method == "POST":
        if "token" in request.GET and request.GET["token"]:
            payload = {
                "password": request.POST["password"],
                "confirmPassword": request.POST["confirmPassword"],
            }
            response, error = _make_api_request(
                f"{API_BASE_URL}/auth/reset-password/reset?token={request.GET['token']}",
                method=requests.post,
                body=payload,
            )
            if isinstance(response, str) and re.match(".*uccess.*", response):
                messages.success(request, _("Password change successful"))
                return redirect("login")
            if isinstance(response, str) and re.match(".*invalid.*", response.lower()):
                messages.error(request, _("Invalid token"))
                return redirect("login")
            if error:
                messages.error(request, _("API error"))
                return redirect("login")
            messages.warning(request, _("Passwords are invalid"))
            return render(request, "reset_password_form.html")
        payload = {"email": request.POST["email"]}
        text, error = _make_api_request(
            f"{API_BASE_URL}/auth/reset-password",
            requests.post,
            body=payload,
        )
        __import__("pdb").set_trace()
        if error:
            messages.error(request, _("Invalid email"))
        elif isinstance(text, str) and re.match("^.*success.*", text.lower()):
            messages.success(request, _("Message sent, check your spam folder"))
        else:
            messages.error(request, _("Unknown error"))
    if "token" in request.GET and request.GET["token"]:
        return render(request, "reset_password_form.html")
    return render(request, "reset_password.html")
