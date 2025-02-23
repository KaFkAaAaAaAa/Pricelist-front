from django.urls import path

from . import views

# pdf/

urlpatterns = [
    path("example-offer/", views.example_offer, name="example-offer"),
]
