from math import floor
from typing import Iterable
from uuid import UUID

import requests
from django.http import HttpResponseServerError
from django.http.response import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .forms import LoginForm, NewAdminForm, PasswordResetForm, RegisterForm
from .settings import ADMIN_GROUPS, API_BASE_URL, CLIENT_GROUPS, GROUPS_ROMAN

# TODO: JSON errors -> if json error then redirect(login)


def _price_to_float(price: int) -> float:
    return price / 100


def _amount_to_float(amount: int) -> float:
    return amount / 10


def _price_to_display(price: float) -> str:
    return f"{price / 100:.2f}"


def _amount_to_display(amount: float) -> str:
    return f"{amount / 10:.1f}"


def _amount_to_store(amount: str) -> int:
    return int(floor(float(amount) * 10))


def _price_to_store(price: str) -> int:
    return int(floor(float(price) * 100))


def _api_error_interpreter(status_code, msg_404=None, msg_401=None, msg_500=None):
    """Interpreter for api error response status code. It renders error response pages.
    If response code is not either 404 or 401, it uses HttpResponseServerError"""
    output = False
    if status_code == 404:
        output = HttpResponseNotFound(msg_404) if msg_404 else HttpResponseNotFound()
    elif status_code in (401, 403):
        output = HttpResponseForbidden(msg_401) if msg_401 else HttpResponseForbidden()
    elif status_code != 200:
        output = (
            HttpResponseServerError(msg_500) if msg_500 else HttpResponseServerError()
        )
    return output


def _make_api_request(url, method=requests.get, headers=None, body=None):
    """Function makes request for api and return json body of response, if
    the response is an error or api response can't be parsed using .json()
    function returns Error HTTP response as a second value """
    response = method(
            url,
            headers=headers,
            json=body,
    )
    try:
        return response.json(), _api_error_interpreter(response.status_code)
    except:
        return {}, _api_error_interpreter(500)


def favicon():
    """render 404 for favicon request"""
    return HttpResponseNotFound()


def _get_auth(token):
    """helper func in authorization process, returns null when user
    is not authenticated, and a dictiornary with user's data"""
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


def _group_to_roman(group_to_translate):
    """Return (str) roman group name, by full group name,
    if group name invalid return null"""
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
    """logout"""
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
                "clientBankNumber": form.cleaned_data["clientBankNumber"],
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
                "clientBankNumber": request.POST["clientBankNumber"],
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
            "clientBankNumber": logged.get("clientBankNumber"),
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
        for name in admins:
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
        return render(
            request,
            "assign_admin.html",
            {"email": user_email, "error": "API error!"},
        )
    return render(
        request, "assign_admin.html", {"email": user_email, "admins": admins.keys()}
    )


def activate_user(request, user_id):
    token = request.session.get("token")
    auth = _get_auth(token)
    if not auth or auth["email"] == "anonymousUser":
        request.session.flush()
        return redirect("login")
    headers = auth["headers"]

    response = requests.get(f"{API_BASE_URL}/users/admin/{user_id}", headers=headers)
    user_email = response.json()["userEmail"]
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
        return render(
            request,
            "activate_user.html",
            {"email": user_email, "error": "API error!"},
        )
    return render(
        request,
        "activate_user.html",
        {
            "email": user_email,
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
        raise HttpResponseNotFound
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
        raise HttpResponseNotFound
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
    # if response.status_code == 200:
    #     return redirect("client_list")
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
                "clientBankNumber": form.cleaned_data["clientBankNumber"],
            }
            response = requests.post(
                f"{API_BASE_URL}/auth/register", json=payload, headers=headers
            )
            if response.status_code == 200:
                return redirect("client_list")
            return render(
                request,
                "new_client.html",
                {"form": form, "error": "Adding new user failed."},
            )
    else:
        form = RegisterForm()
        for field in form.visible_fields():
            if "placeholder" in field.widget.attrs:
                field.widget.attrs["placeholder"] = field.widget.attrs[
                    "placeholder"
                ].replace(_("your "), "")
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
            "clientBankNumber": request.POST["clientBankNumber"],
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
