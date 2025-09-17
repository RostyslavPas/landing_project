from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_payment, name="create_payment"),
    path("callback/", views.payment_callback, name="payment_callback"),
    path('', views.index, name='index'),        # desktop
    path('mobile/', views.mobile, name='mobile')  # mobile
]
