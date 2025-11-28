from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from payments import views


def home(request):
    return render(request, "index.html")


def mobile_home(request):
    return render(request, "mobile.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    # path("", home, name="home"),
    path("mobile/", mobile_home, name="mobile"),

    # ✅ шлях до сторінки підписки
    path("", views.subscription, name="subscription"),

    # ✅ залишай include в кінці — Django читає зверху вниз
    path("", include("payments.urls")),
]