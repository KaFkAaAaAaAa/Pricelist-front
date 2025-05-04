from django import forms
from django.utils.translation import gettext_lazy as _

from Pricelist.settings import ADMIN_GROUPS, SUPPORT_GROUPS


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        max_length=100,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": _("Email")}
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        max_length=100,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Password")}
        ),
    )


class RegisterForm(forms.Form):
    # TODO: remove your when used in add client
    userFirstName = forms.CharField(
        label=_("First Name:"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your first name"),
            }
        ),
    )
    userLastName = forms.CharField(
        label=_("Last Name:"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your last name"),
            }
        ),
    )
    userEmail = forms.EmailField(
        label=_("Email:"),
        max_length=100,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": _("Enter your email")}
        ),
    )
    userTelephoneNumber = forms.CharField(
        label=_("Telephone number:"),
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your telephone number"),
            }
        ),
    )
    clientCompanyName = forms.CharField(
        label=_("Company name:"),
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your company name"),
            }
        ),
    )
    clientStreet = forms.CharField(
        label=_("Street:"),
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your street"),
            }
        ),
    )
    clientCode = forms.CharField(
        label=_("Code:"),
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your code"),
            }
        ),
    )
    clientCity = forms.CharField(
        label=_("City") + ":",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your city"),
            }
        ),
    )
    clientCountry = forms.CharField(
        label=_("Country") + ":",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your country"),
            }
        ),
    )


class NewUserForm(forms.Form):
    userFirstName = forms.CharField(
        label=_("First Name") + ":",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your first name"),
            }
        ),
    )
    userLastName = forms.CharField(
        label=_("Last Name") + ":",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your last name"),
            }
        ),
    )
    userEmail = forms.EmailField(
        label=_("Email") + ":",
        max_length=100,
        widget=forms.EmailInput(
            attrs={"class": "form-control",
                   "placeholder": _("Enter your email")}
        ),
    )
    userGroup = forms.ChoiceField(
        choices=[(group, group) for group in (SUPPORT_GROUPS + ADMIN_GROUPS)],
        label=_("Group") + ":",
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class UserActivateForm(forms.Form):
    admin = forms.SelectMultiple()
    group = forms.SelectMultiple(
        choices=["I", "II", "III", "IV"],
    )

    def UserActivateForm(self, admins):
        self.admin.choices = admins


class PasswordResetForm(forms.Form):
    password = forms.CharField(
        label=_("Password"),
        max_length=100,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Password"),
            }
        ),
    )
    confirmPassword = forms.CharField(
        label=_("Confirm Password"),
        max_length=100,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Confirm Password"),
            }
        ),
    )


class EditProfileForm(forms.Form):
    userFirstName = forms.CharField(
        label= _("First Name:"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
    userLastName = forms.CharField(
        label= _("Last Name:"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
    userEmail = forms.EmailField(
        label="Email:",
        max_length=100,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
    userTelephoneNumber = forms.CharField(
        label= _("Telephone number:"),
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
