from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from payments.views import index, mobile


def home(request):
    return render(request, "index.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("", index, name="index"),
    path("mobile/", mobile, name="mobile")
]
