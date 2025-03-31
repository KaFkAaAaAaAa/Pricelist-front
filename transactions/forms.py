from django import forms
from django.forms.widgets import Widget
from django.utils.translation import gettext_lazy as _

STATUSES = ["PROPOSITION", "OFFER", "PROGNOSE", "FINAL"]


class StatusForm(forms.Form):

    def __init__(self, init_status=STATUSES[0], *args, **kwargs):
        super().__init__(*args, **kwargs)
        if init_status.upper() not in STATUSES:
            raise ValueError
        __import__("pdb").set_trace()
        if init_status == "FINAL":
            return
        self.fields["select_status"].choices = [
            (s, s.lower())
            for s in STATUSES
            if STATUSES.index(s) <= STATUSES.index(init_status.upper()) + 1
        ]
        self.fields["select_status"].initial = self.fields["select_status"].choices[-1]

    select_status = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )


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
    delivery_date = forms.DateField(
        label=_("Delivery date") + ":",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            },
        ),
    )
    delivery_price = forms.DecimalField(
        label=_("Delivery price") + ":",
        widget=forms.NumberInput(
            attrs={
                "min": "0.1",
                "class": "form-control",
            }
        ),
    )
    prognose_info = forms.CharField(
        label=_("Additional info about transaction") + ":",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
    )
    delivery_info = forms.CharField(
        label=_("Delivery info") + ":",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
    )
