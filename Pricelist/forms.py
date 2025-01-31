from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=100,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email"}
        ),
    )
    password = forms.CharField(
        label="Password",
        max_length=100,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        ),
    )


class RegisterForm(forms.Form):
    # TODO: remove your when used in add client

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
    userTelephoneNumber = forms.CharField(
        label="Telephone number:",
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your telephone number",
            }
        ),
    )
    clientCompanyName = forms.CharField(
        label="Company name:",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter your company name"}
        ),
    )
    clientStreet = forms.CharField(
        label="Street:",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter your street"}
        ),
    )
    clientCode = forms.CharField(
        label="Code:",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter your code"}
        ),
    )
    clientCity = forms.CharField(
        label="City:",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter your city"}
        ),
    )
    clientBankNumber = forms.CharField(
        label="Bank account number:",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your bank account number",
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
