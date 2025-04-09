from dataclasses import dataclass
from functools import wraps
from http.client import INTERNAL_SERVER_ERROR
from json import JSONDecodeError
from math import floor

import requests
from django.contrib import messages
from django.http.response import (
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from Pricelist.settings import ADMIN_GROUPS, API_BASE_URL, CLIENT_GROUPS, GROUPS_ROMAN

RESPONSE_FORBIDDEN = HttpResponseForbidden(
    f"<h1>{_('You do not have access to that page')}<h1>".encode("utf-8")
)


def _price_to_float(price: int) -> float:
    return price / 100


def _amount_to_float(amount: int) -> float:
    return amount / 10


def _price_to_display(price: float) -> str:
    return f"{price / 100:.2f}"


def _amount_to_display(amount: float) -> str:
    return f"{amount / 10:.1f}"


def _amount_to_store(amount: str) -> int:
    if amount in ("", "0", False):
        amount = "0"
    return int(floor(float(amount) * 10)) if amount else 0


def _price_to_store(price: str) -> int:
    if price in ("", "0", False):
        price = "0"
    return int(floor(float(price) * 100)) if price else 0


def _api_error_interpreter(status_code, msg_404=None, msg_401=None, msg_500=None):
    """Interpreter for api error response status code. It renders error response pages.
    If response code is not either 404 or 401, it uses HttpResponseServerError"""
    output = False
    if status_code == 404:
        output = HttpResponseNotFound(msg_404) if msg_404 else HttpResponseNotFound(b"")
    elif status_code in (401, 403):
        output = (
            HttpResponseForbidden(msg_401) if msg_401 else HttpResponseForbidden(b"")
        )
    elif status_code != 200:
        output = (
            HttpResponseServerError(msg_500)
            if msg_500
            else HttpResponseServerError(b"")
        )
    return output


def _make_api_request(url, method=requests.get, headers=None, body=None):
    """Function makes request for api and return json body of response, if
    the response is an error or api response can't be parsed using .json()
    function returns Error HTTP response as a second value"""
    response = None
    try:
        response = method(url, headers=headers, json=body, timeout=60)
        if response:
            return response.json(), _api_error_interpreter(response.status_code)
        return False, _api_error_interpreter(INTERNAL_SERVER_ERROR)
    except JSONDecodeError:
        if response:
            return response.text, _api_error_interpreter(
                response.status_code
            )  # response cannot be unbound and throw JSONDecodeError but the warning is bugging me
        return False, _api_error_interpreter(INTERNAL_SERVER_ERROR)
    except requests.exceptions.Timeout:
        print("ERROR: API request timeout")
        return False, _api_error_interpreter(INTERNAL_SERVER_ERROR)
    except:
        return False, _api_error_interpreter(INTERNAL_SERVER_ERROR)


def _get_auth(token):
    """helper func in authorization process, returns {} when user
    is not authenticated, and a dictiornary with user's data"""
    if not token:
        return {}
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/auth/whoami/", headers=headers)
    try:
        if response.status_code != 200:
            return {}
        auth = response.json()
        auth["token"] = token
        auth["headers"] = headers
        auth["group"] = auth["group"].rstrip("]").lstrip("[")
        return auth
    except:
        return {}


def _group_to_roman(group_to_translate):
    """Return (str) roman group name, by full group name,
    if group name invalid return null"""
    for i, group_full in enumerate(CLIENT_GROUPS):
        if group_to_translate == group_full:
            return GROUPS_ROMAN[i]
    return False


def _get_headers(request):
    try:
        return request.session["auth"]["headers"]
    except KeyError:
        return {}


def _get_group(request):
    try:
        return request.session["auth"]["group"]
    except KeyError:
        return {}


def _is_admin(request):
    try:
        return request.session["auth"]["group"] in ADMIN_GROUPS
    except KeyError:
        return False


def _is_client(request):
    try:
        return request.session["auth"]["group"] in CLIENT_GROUPS
    except KeyError:
        return False


def require_auth(view_func):
    """Checks if user is authorizied and authenticated based on api request. It sets session["auth"]"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            token = request.session["token"]
        except KeyError:
            return redirect("login")
        auth = _get_auth(token)
        if not auth or auth["email"] == "anonymousUser":
            request.session.flush()
            return redirect("login")
        if auth["group"] == "UNASSIGNED":
            request.session.flush()
            messages.warning(
                request, _("User not activated yet, wait for information on your email")
            )
            return redirect("login")
        request.session["auth"] = auth
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_group(allowed_groups: list):
    """Checks if user that requests an asset is a member of a group based on session["auth"]"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                auth = request.session["auth"]
            except KeyError:
                return RESPONSE_FORBIDDEN
            if auth.get("group") not in allowed_groups:
                return RESPONSE_FORBIDDEN
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


@dataclass
class Page:
    """Spring/JPA page serializer for better readability"""

    content: list
    page_no: int
    page_size: int
    total_elements: int
    total_pages: int
    last: bool

    def __init__(self, api_response: dict) -> None:
        self.content = api_response["content"]
        self.page_no = api_response["pageNo"]
        self.page_size = api_response["pageSize"]
        self.total_elements = api_response["totalElements"]
        self.total_pages = api_response["totalPages"]
        self.last = api_response["last"]

    def __str__(self) -> str:
        return f"PageObject:{self.page_size}:{self.page_no}/{self.total_pages}"
