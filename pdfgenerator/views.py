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


def print_pricelist(request):
    # get date
    # get pricelist
    # get admin_data
    # put in data
    return generate_pdf(request, "price_list_pdf", {}, "pricelist_date")


def generate_pdf(request, template, data, filename="document"):
    """generate pdf response"""

    data["images_root"] = "file://" + str(BASE_DIR)
    data["filename"] = filename
    html_string = render_to_string(template, data)
    font_conf = FontConfiguration()

    pdf_file_path = tempfile.mktemp(suffix=".pdf")

    css = (
        []
        if template == "pricelist-pdf.html"
        else [
            CSS(
                filename=str(STATICFILES_DIRS[0]) + "/css/bootstrap-pdf.css",
                font_config=font_conf,
            ),
        ]
    )

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/").replace("http:", "https:"),
    ).write_pdf(
        pdf_file_path,
        stylesheets=css,
    )
    with open(pdf_file_path, "rb") as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    os.remove(pdf_file_path)
    return response
