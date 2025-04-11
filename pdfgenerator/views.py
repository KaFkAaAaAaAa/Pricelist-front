import logging
import os
import tempfile

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from Pricelist.settings import BASE_DIR, STATICFILES_DIRS

logger = logging.getLogger(__name__)


def example_offer(request):
    items = [
        {
            "itemOrderedSku": "TE01",
            "itemOrderedName": "test",
            "itemOrderedAmount": 1.2,
            "itemOrderedPrice": 0.4,
            "total": 0.41,
        },
        {
            "itemOrderedSku": "TE02",
            "itemOrderedName": "test",
            "itemOrderedAmount": 1.8,
            "itemOrderedPrice": 0.6,
            "total": 1.1,
        },
    ]
    client = {
        "clientCompanyName": "Firma Sp. z o.o.",
        "clientStreet": "ul. Test 42",
        "clientCode": "55-555",
        "clientCity": "Wroclaw",
        "clientCountry": "Poland",
    }

    total = {"mass": 3, "price": 1.51}
    date = "19-02-2025"
    data = {"items": items, "user": client, "total": total, "date": date}

    for product in items:
        product["sum"] = product["amount"] * product["price"]

    total_sum = sum(product["amount"] * product["price"] for product in items)
    data["total_sum"] = total_sum
    if request.GET["format"] == "pdf":
        return generate_pdf(request, "pdf_offer.html", data)
    return render(request, "pdf_offer.html", data)


def prognose_offer(request):
    items = [
        {
            "sku": "TE01",
            "name": "test",
            "amount": 1.2,
            "price": 0.4,
            "total": 0.41,
        },
        {
            "sku": "TE02",
            "name": "test",
            "amount": 1.8,
            "price": 0.6,
            "total": 1.1,
        },
    ]
    client = {
        "clientCompanyName": "Firma Sp. z o.o.",
        "clientStreet": "ul. Test 42",
        "clientCode": "55-555",
        "clientCity": "Wroclaw",
        "clientCountry": "Poland",
    }

    total = {"weight": 3, "price": 1.51}
    date = "19-02-2025"
    data = {"items": items, "u": client, "total": total, "date": date}

    for product in items:
        product["sum"] = product["amount"] * product["price"]

    total_sum = sum(product["amount"] * product["price"] for product in items)
    data["total_sum"] = total_sum
    if request.GET["format"] == "pdf":
        return generate_pdf(request, "pdf_prognose.html", data)
    return render(request, "pdf_prognose.html", data)


def final_offer(request):
    items = [
        {
            "sku": "TE01",
            "name": "test",
            "amount": 1.2,
            "price": 0.4,
            "total": 0.41,
        },
        {
            "sku": "TE02",
            "name": "test",
            "amount": 1.8,
            "price": 0.6,
            "total": 1.1,
        },
    ]
    client = {
        "clientCompanyName": "Firma Sp. z o.o.",
        "clientStreet": "ul. Test 42",
        "clientCode": "55-555",
        "clientCity": "Wroclaw",
        "clientCountry": "Poland",
    }

    total = {"weight": 3, "price": 1.51}
    date = "19-02-2025"
    data = {"items": items, "u": client, "total": total, "date": date}

    for product in items:
        product["sum"] = product["amount"] * product["price"]

    total_sum = sum(product["amount"] * product["price"] for product in items)
    data["total_sum"] = total_sum
    if request.GET["format"] == "pdf":
        return generate_pdf(request, "pdf_final.html", data)
    return render(request, "pdf_final.html", data)


def generate_pdf(request, template, data, filename="document"):
    """generate pdf response"""

    data["images_root"] = "file://" + str(BASE_DIR)
    data["filename"] = filename
    html_string = render_to_string(template, data)
    font_conf = FontConfiguration()

    pdf_file_path = tempfile.mktemp(suffix=".pdf")
    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(
        pdf_file_path,
        stylesheets=[
            CSS(
                filename=str(STATICFILES_DIRS[0]) + "/css/bootstrap-pdf.css",
                font_config=font_conf,
            ),
            # CSS(
            #     filename=str(STATICFILES_DIRS[0]) + "/css/pdf.css",
            #     font_config=font_conf,
            # ),
        ],
    )

    with open(pdf_file_path, "rb") as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
    os.remove(pdf_file_path)
    return response
