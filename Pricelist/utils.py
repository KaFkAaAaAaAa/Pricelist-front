import logging
import math
import re
from dataclasses import dataclass
from functools import wraps
from http.client import INTERNAL_SERVER_ERROR
from json import JSONDecodeError
from math import floor

import requests
from django.contrib import messages
from django.forms import UUIDField
from django.http.response import (
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from Pricelist.settings import (
    ADMIN_GROUPS,
    API_BASE_URL,
    CLIENT_GROUPS,
    GROUPS_ROMAN,
    LOGGING_CONFIG,
    SUPPORT_GROUPS,
)

RESPONSE_FORBIDDEN = HttpResponseForbidden(
    f"<h1>{_('You do not have access to that page')}<h1>".encode("utf-8")
)
logger = logging.getLogger(__name__)


def _price_to_float(price: int) -> float:
    return price / 100


def _amount_to_float(amount: int) -> float:
    return amount / 10


def _price_to_display(price: float) -> str:
    return f"{price / 100:.2f}".replace(",", ".")


def _amount_to_display(amount: float) -> str:
    return f"{amount / 10:.1f}".replace(",", ".")


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
    except ConnectionRefusedError:
        logger.error(
            "Connection error, API is unreachable; %s %s", method.__name__.upper(), url
        )
        return HttpResponseServerError(b"Internal server error")
    except JSONDecodeError:
        if response:
            return response.text, _api_error_interpreter(
                response.status_code
            )  # response cannot be unbound and throw JSONDecodeError but the warning is bugging me
        return False, _api_error_interpreter(INTERNAL_SERVER_ERROR)
    except requests.exceptions.Timeout:
        logger.error("API request timeout; %s %s", method.__name__.upper(), url)
        return False, _api_error_interpreter(INTERNAL_SERVER_ERROR)
    except:
        logger.error("Unknown error request %s %s", method.__name__.upper(), url)
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
        logger.error(
            "Api response on /auth/whoami/: [%s] %s",
            response.status_code,
            response.text,
        )
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


def _is_support(request):
    try:
        return request.session["auth"]["group"] in SUPPORT_GROUPS
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
    first: bool
    prev: int
    next: int

    def __init__(self, api_response: dict) -> None:
        # pages in front 1-indexed, pages in back 0-indexed
        self.content = api_response["content"]
        self.page_no = api_response["pageNo"] + 1
        self.page_size = api_response["pageSize"]
        self.total_elements = api_response["totalElements"]
        self.total_pages = api_response["totalPages"]
        self.last = self.page_no == self.total_pages
        self.first = self.page_no == 1
        self.prev = self.page_no - 1 if not self.first else 0
        self.next = self.page_no + 1 if not self.first else self.total_pages

    def __str__(self) -> str:
        return f"PageObject:{self.page_size}:{self.page_no}/{self.total_pages}"


@dataclass
class ItemOrdered:
    """ItemOrderedModel used by API"""

    uuid: str | None
    sku: str
    accounting_number: str | None
    name: str
    price: int
    amount: int
    additional_info: str
    transaction_id: str

    def __init__(self, api_response: dict) -> None:
        self.uuid = api_response.get("uuid", None)
        self.sku = api_response.get("sku", "")
        self.accounting_number = api_response.get("accountingNumber", None)
        self.name = api_response.get("name", "")
        self.price = api_response.get("price", 0)
        self.amount = api_response.get("amount", 0)
        self.additional_info = api_response.get("additionaInfo", "")
        self.transaction_id = api_response.get("transactionId", "")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        if self is other:
            return True
        return (
            self.sku == other.sku
            and self.accounting_number == other.accounting_number
            and self.name == other.name
            and self.price == other.price
            and self.amount == other.amount
            and self.additional_info == other.additional_info
        )


def _get_page_param(request, first=True):
    """return ?page_no=GET["page"] or empty str
    if no page number was passed in the request"""
    if "page" not in request.GET.keys():
        return ""
    page_no = int(request.GET["page"]) - 1
    page_no = max(page_no, 0)
    return f"?pageNo={page_no}" if first else f"&pageNo={page_no}"


def admin_groups_context(request):
    return {"ADMIN_GROUPS": ADMIN_GROUPS}


def client_groups_context(request):
    return {"CLIENT_GROUPS": CLIENT_GROUPS}


def support_groups_context(request):
    return {"SUPPORT_GROUPS": SUPPORT_GROUPS}


def parse_logs_login_action(page_no, page_size):

    login_logs = []

    with open("pricelist-front.log", "r") as l:
        logfile_lines = l.readlines()

    for line in logfile_lines:
        if re.match(r"logged in succ", line):
            login_logs.append(line)

    first = page_size * page_no
    last = first + page_size - 1
    page_init = {
        "content": login_logs[first:last],
        "pageNo": page_no,
        "pageSize": page_size,
        "totalElements": len(login_logs),
        "totalPages": math.ceil(len(login_logs) / page_size),
    }
    page = Page(page_init)

    return page
