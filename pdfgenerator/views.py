import os
import tempfile

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from weasyprint import HTML

# Create your views here.


def example_offer(request):

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
    # if request.GET["format"] == "pdf":
    #     return generate_pdf("pdf_offer.html", data)
    return render(request, "pdf_offer.html", data)


def generate_pdf(template, data, filename="document"):
    """generate pdf response"""

    html_string = render_to_string(template, data)

    pdf_file_path = tempfile.mktemp(suffix=".pdf")
    HTML(string=html_string).write_pdf(pdf_file_path)

    with open(pdf_file_path, "rb") as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
    os.remove(pdf_file_path)
    return response
