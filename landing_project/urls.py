from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include


def home(request):
    return render(request, "index.html")

def mobile_home(request):
    return render(request, "mobile.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("mobile/", mobile_home, name="mobile"),
    path('', include('payments.urls')),
]