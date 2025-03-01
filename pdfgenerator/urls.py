from django.urls import path

from . import views

# pdf/

urlpatterns = [
    path("example-offer/", views.example_offer, name="example-offer"),
    path("prognose/", views.prognose_offer, name="prognose"),
    path("final/", views.final_offer, name="final"),
]
