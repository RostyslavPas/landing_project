from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('mobile/', views.mobile, name='mobile'),
    path('submit-ticket/', views.submit_ticket_form, name='submit_ticket'),
    path('wayforpay/callback/', views.wayforpay_callback, name='wayforpay_callback'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
]
