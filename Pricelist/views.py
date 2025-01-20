import requests
from django.shortcuts import render, redirect
from .forms import LoginForm, RegisterForm

API_BASE_URL = "http://127.0.0.1:8888"  # Replace with your API base URL

# TODO: JSON errors -> if json error then redirect(login)


# Login View
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            payload = {
                "email": form.cleaned_data['email'],
                "password": form.cleaned_data['password']
            }
            response = requests.post(f"{API_BASE_URL}/auth/login", json=payload)
            if response.status_code == 200:
                request.session['token'] = response.json().get('token')
                return redirect('price_list')
            else:
                return render(request, 'login.html',
                              {'form': form, 'error': "Invalid credentials"})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


# Logout View
def logout_view(request):
    request.session.flush()
    return redirect('login')


# Register View
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            payload = {
                "userEmail": form.cleaned_data['userEmail'],
                "userTelephoneNumber": form.cleaned_data['userTelephoneNumber'],
                "clientCompanyName": form.cleaned_data['clientCompanyName'],
                "clientStreet": form.cleaned_data['clientStreet'],
                "clientCode": form.cleaned_data['clientCode'],
                "clientCity": form.cleaned_data['clientCity'],
                "clientBankNumber": form.cleaned_data['clientBankNumber'],
            }
            response = requests.post(f"{API_BASE_URL}/auth/register",
                                     json=payload)
            if response.status_code == 200:
                return redirect('login')
            else:
                return render(request, 'register.html',
                              {'form': form, 'error': "Registration failed."})
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def price_list(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}
    # TODO: lang and sort params
    response = requests.get(f"{API_BASE_URL}/items/price-list?lang=EN",
                            headers=headers)
    items = response.json() if response.status_code == 200 else []
    for item in items:
        item["price"] /= 100
    return render(request, 'price_list.html', {"items": items})


def item_detail(request, item_sku):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(f"{API_BASE_URL}/items/{item_sku}", headers=headers)
    if response.status_code == 200:
        item = response.json()
        return render(request, 'item_detail.html', {'item': item})
    else:
        return render(request, 'item_detail.html', {'error': "Item not found."})


# admin views

# TODO: add is-admin endpoint to API bc @login_required doesn't work,
#   and too many work-arounds are needed to make it work
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')


def admin_items(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/items/admin/", headers=headers)
    items = response.json() if response.status_code == 200 else []
    return render(request, 'item_list.html', {'items': items})


def edit_item(request, item_sku):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}
    if request.method == "POST":
        payload = {
            "itemSku": request.POST.get('itemSku'),
            "itemGroup": request.POST.get('itemGroup'),
            "itemImgPath": request.POST.get('itemImgPath'),
            "itemName": {
                "DE": request.POST.get('DE-n'),
                "EN": request.POST.get('EN-n'),
                "IT": request.POST.get('IT-n'),
                "FR": request.POST.get('FR-n'),
                "PL": request.POST.get('PL-n'),
            },
            "itemDescription": {
                "DE": request.POST.get('DE-d'),
                "EN": request.POST.get('EN-d'),
                "IT": request.POST.get('IT-d'),
                "FR": request.POST.get('FR-d'),
                "PL": request.POST.get('PL-d'),
            },
            "itemPrice": request.POST.get('itemPrice').split(','),
        }
        payload["itemPrice"] = [int(price) for price in payload["itemPrice"]]
        response = requests.put(f"{API_BASE_URL}/items/admin/{item_sku}",
                                headers=headers, json=payload)
        if response.status_code == 200:
            return redirect('item_list')
        else:
            # error = payload.error
            return redirect('item_list')
    else:
        response = requests.get(f"{API_BASE_URL}/items/admin/{item_sku}",
                                headers=headers)
        item = response.json() if response.status_code == 200 else None
        if item:
            return render(request, 'edit_item.html', {'item': item})
        else:
            return render(request, 'edit_item.html',
                          {'error': 'Item not found!'})


def delete_item(request, item_sku):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{API_BASE_URL}/items/admin/{item_sku}",
                               headers=headers)
    # TODO: Errors and success messages
    if response.status_code == 200:
        return redirect('item_list')
    else:
        return redirect('item_list')


def add_item(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}
    # TODO: Errors and success messages
    if request.method == "POST":
        payload = {
            "itemSku": request.POST.get('itemSku'),
            "itemGroup": request.POST.get('itemGroup'),
            "itemImgPath": request.POST.get('itemImgPath'),
            "itemName": {
                "DE": request.POST.get('DE-n'),
                "EN": request.POST.get('EN-n'),
                "IT": request.POST.get('IT-n'),
                "FR": request.POST.get('FR-n'),
                "PL": request.POST.get('PL-n'),
            },
            "itemDescription": {
                "DE": request.POST.get('DE-d'),
                "EN": request.POST.get('EN-d'),
                "IT": request.POST.get('IT-d'),
                "FR": request.POST.get('FR-d'),
                "PL": request.POST.get('PL-d'),
            },
            "itemPrice": request.POST.get('itemPrice'),
        }
        payload["itemPrice"] = [int(price) for price in payload["itemPrice"].split(',')]
        response = requests.post(f"{API_BASE_URL}/items/admin/",
                                 headers=headers, json=payload)
        if response.status_code == 200:
            return redirect('item_list')
        else:
            return redirect('item_list')
    else:
        return render(request, 'add_item.html')
