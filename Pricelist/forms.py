from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)


class RegisterForm(forms.Form):
    userEmail = forms.EmailField(label="Email:", max_length=100)
    userTelephoneNumber = forms.CharField(label="Telephone number:", max_length=15)
    clientCompanyName = forms.CharField(label="Company name:", max_length=100)
    clientStreet = forms.CharField(label="Street:", max_length=100)
    clientCode = forms.CharField(label="Code:", max_length=100)
    clientCity = forms.CharField(label="City:", max_length=100)
    clientBankNumber = forms.CharField(label="Bank number:", max_length=50)

    # TODO: validate
    
