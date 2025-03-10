from django import forms
from django.utils.translation import gettext_lazy as _


class ItemForm(forms.Form):
    sku = forms.CharField(
        label=_("SKU") + ":",
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "SKU"}),
    )
    name = forms.CharField(
        label=_("Name") + ":",
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Name")}
        ),
    )
    price = forms.DecimalField(
        decimal_places=2,
        label=_("Price") + ":",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "price",
                "min": "0.01",
                "value": "0.01",
                "onchange": "updateTotal();",
            },
        ),
    )
    amount = forms.DecimalField(
        label=_("Amount") + ":",
        decimal_places=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "amount",
                "min": "0.1",
                "value": "0.1",
                "onchange": "updateTotal();",
            },
        ),
    )
    additionalInfo = forms.CharField(
        label=_("Additional info") + ":",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
            }
        ),
        required=False,
    )


class PrognoseFrom(forms.Form):
    plates_list = forms.CharField(
        label=_("Plates") + ":",
        widget=forms.HiddenInput(),
        required=False,
    )
