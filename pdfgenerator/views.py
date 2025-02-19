import pdfkit
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

# Create your views here.


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
    pdf = pdfkit.from_string(html_string, False)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
