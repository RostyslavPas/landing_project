from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('mobile/', views.mobile, name='mobile'),
    path('submit-ticket/', views.submit_ticket_form, name='submit_ticket'),
    path('submit-ticket-form/', views.submit_ticket_form, name='submit_ticket_form'),
    path("payment/result/", views.payment_result, name="payment_result"),
    path("payment/callback/", views.wayforpay_callback, name="wayforpay_callback"),
    path('verify/ticket/<str:order_ref>/', views.verify_ticket, name='verify_ticket'),
    path('verify/admin/<str:order_ref>/', views.verify_admin_ticket, name='verify_admin_ticket'),
    path('verify/mark-used/', views.mark_ticket_used, name='mark_ticket_used'),
    path('verify/check/<str:order_ref>/', views.verify_check, name='verify_check'),
    path('keycrm/info/', views.keycrm_info, name='keycrm_info'),
]
