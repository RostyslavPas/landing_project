from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('mobile/', views.mobile, name='mobile'),
    path('submit-ticket/', views.submit_ticket_form, name='submit_ticket'),
    path('submit-ticket-form/', views.submit_ticket_form, name='submit_ticket_form'),
    path("payment/result/", views.payment_result, name="payment_result"),
    path("payment/callback/", views.wayforpay_callback, name="wayforpay_callback")
]
