from django import forms
from django.utils.translation import gettext_lazy as _


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
        label=_("City:"),
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your city"),
            }
        ),
    )
    clientCountry = forms.CharField(
        label=_("Country:"),
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your country"),
            }
        ),
    )
    clientBankNumber = forms.CharField(
        label=_("Bank account number:"),
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your bank account number"),
            }
        ),
    )


class NewAdminForm(forms.Form):
    userFirstName = forms.CharField(
        label="First Name:",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your first name",
            }
        ),
    )
    userLastName = forms.CharField(
        label="Last Name:",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your last name",
            }
        ),
    )
    userEmail = forms.EmailField(
        label="Email:",
        max_length=100,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your email"}
        ),
    )
    # TODO: validate


class UserActivateForm(forms.Form):
    admin = forms.SelectMultiple()
    group = forms.SelectMultiple(
        choices=["I", "II", "III", "IV"],
    )

    def UserActivateForm(self, admins):
        self.admin.choices = admins


class PasswordResetForm(forms.Form):
    password = forms.CharField(
        label="Password",
        max_length=100,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        ),
    )
    confirmPassword = forms.CharField(
        label="Confirm Password",
        max_length=100,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm Password"}
        ),
    )


class EditProfileForm(
    forms.Form,
):
    userFirstName = forms.CharField(
        label="First Name:",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
    userLastName = forms.CharField(
        label="Last Name:",
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
        label="Telephone number:",
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
