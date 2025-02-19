from django.urls import path

from . import views

# transactions/

urlpatterns = [
    path("example-offer/", views.example_offer, name="example-offer"),
]
