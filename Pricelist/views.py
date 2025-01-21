import requests
from django.shortcuts import render, redirect
from .forms import LoginForm, RegisterForm
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from math import floor

API_BASE_URL = "http://127.0.0.1:8888"  # Replace with your API base URL

GROUPS = ["FIRST", "SECOND", "THIRD", "FOURTH"]

GROUPS_ROMAN = ["I", "II", "III", "IV"]

LANGS = ["PL", "EN", "DE", "FR", "IT"]

CATEGORIES = {
        "PL": ""
        }

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
        item["price"] = f"{item['price'] / 100:.2f}"
    return render(request, 'price_list.html', {"items": items})


def item_detail(request, item_sku):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(f"{API_BASE_URL}/items/{item_sku}", headers=headers)
    if response.status_code == 200:
        item = response.json()
        item["price"] = f"{item['price'] / 100:.2f}"
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
    for item in items:
        item["itemPrice"] = [f"{group_price / 100:.2f}"
                             for group_price in item["itemPrice"]]
        item["itemPrice"] = '/'.join(item["itemPrice"])
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
            "itemPrice":
                [int(floor(float(request.POST.get(f"itemPrice-{i}"))*100))
                    for i in range(1, 5)],
        }
        if request.POST.get('deleteItem'):
            # print(request.POST.get('deleteItem'))
            payload["itemImgPath"] = ""
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
            item["itemPrice"] = [f"{group_price / 100:.2f}"
                                 for group_price in item["itemPrice"]]
            return render(request, 'edit_item.html',
                          {
                              'item': item,
                              'range': range(1, 5),
                          })
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


def upload_image(request, item_sku):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    headers = {"Authorization": f"Bearer {token}"}

    uploaded_url = None
    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']
        fs = FileSystemStorage()
        filename = fs.save(f"{item_sku}_{image.name}", image)
        uploaded_url = fs.url(filename)
        response = requests.post(f"{API_BASE_URL}/items/admin/{item_sku}/img-path",
                                 headers=headers, data={"path": uploaded_url})
        # TODO: Error handling
        if response.status_code == 200:
            pass
        else:
            pass
    return render(request, 'upload_image.html',
                  {'uploaded_url': uploaded_url})


def delete_image(request, item_sku, item_path):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    headers = {"Authorization": f"Bearer {token}"}
    # unfinished bc it might not be needed
    fs = FileSystemStorage()
    fs.delete(item_path)


def add_item(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')

    headers = {"Authorization": f"Bearer {token}"}
    # TODO: Errors and success messages
    if request.method == "POST":
        # image = request.FILES['image']
        # fs = FileSystemStorage()
        item_sku = request.POST.get('itemSku')
        # filename = fs.save(f"{item_sku}_{image.name}", image)
        # uploaded_url = fs.url(filename)
        payload = {
            "itemSku": item_sku,
            "itemGroup": request.POST.get('itemGroup'),
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
            "itemPrice":
                [request.POST.get(f"itemPrice-{i}") for i in range(1, 5)],
        }
        for price_group in payload["itemPrice"]:
            price_group = int(100*float(price_group))
        response = requests.post(f"{API_BASE_URL}/items/admin/",
                                 headers=headers, json=payload)
        if response.status_code == 200:
            return redirect('upload_image', item_sku)
        else:
            return redirect('item_list')
    else:
        return render(request, 'add_item.html',
                      {"range": range(1, 5)})
