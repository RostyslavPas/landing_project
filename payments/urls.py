from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('mobile/', views.mobile, name='mobile'),
    path('submit-ticket/', views.submit_ticket_form, name='submit_ticket'),
    path('submit-ticket-form/', views.submit_ticket_form, name='submit_ticket_form'),
    path("payment/result/", views.payment_result, name="payment_result"),
    path("payment/callback/", views.wayforpay_callback, name="wayforpay_callback"),
    path('keycrm/info/', views.keycrm_info, name='keycrm_info'),
    path('api/tickets/validate/<int:ticket_id>/', views.validate_ticket_api, name='validate_ticket'),
    path('api/tickets/scan/<int:ticket_id>/', views.scan_ticket_api, name='scan_ticket'),
    path('scanner/', views.scanner_page, name='scanner'),
    path('verify-ticket/<int:ticket_id>/', views.verify_ticket_page, name='verify_ticket'),
]
