import pdfkit
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

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


def _calculate_total_mass(item_list) -> float:
    """calculates total mass of item_list by item.amount"""
    mass = 0
    for item in item_list:
        mass += item.get("amount")
    return mass


def _calculate_totals(item_list) -> float:
    """calculates total for each item in item_list based on item.price and item.amount,
    saves it in item["total"] and returns total of totals"""
    price = 0
    for item in item_list:
        item["total"] = item.get("price") * item.get("amount")
        price += item.get("total")
    return price


def generate_pdf(template, data, filename="document"):
    """generate pdf response"""
    html_string = render_to_string(template, data)
    config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
    pdf = pdfkit.from_string(html_string, False, configuration=config)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
