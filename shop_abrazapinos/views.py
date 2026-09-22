from django.shortcuts import render

from .models import Product


def home(request):
    products = Product.objects.order_by('-created_at')[:6]
    return render(request, 'shop_abrazapinos/home.html', {'products': products})
