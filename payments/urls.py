from django.urls import path
from . import views
from django.views.generic import TemplateView, RedirectView

from .views import get_order_by_token, get_subscription_by_token

urlpatterns = [
    path('', views.subscription, name='subscription_home'),
    path('subscription/', RedirectView.as_view(pattern_name='subscription_home', permanent=True)),
    # 301-редирект з /opening/ на головну
    path('opening/', RedirectView.as_view(pattern_name='subscription_home', permanent=True)),

    # 301-редирект з /opening/mobile/ на головну
    path('opening/mobile/', RedirectView.as_view(pattern_name='subscription_home', permanent=True)),

    path('submit-ticket/', views.submit_ticket_form, name='submit_ticket'),
    path('submit-ticket-form/', views.submit_ticket_form, name='submit_ticket_form'),
    path("payment/result/", views.payment_result, name="payment_result"),
    path("payment/callback/", views.wayforpay_callback, name="wayforpay_callback"),
    path('keycrm/info/', views.keycrm_info, name='keycrm_info'),
    path('api/tickets/validate/<int:ticket_id>/', views.validate_ticket_api, name='validate_ticket'),
    path('api/tickets/scan/<int:ticket_id>/', views.scan_ticket_api, name='scan_ticket'),
    path('scanner/', views.scanner_page, name='scanner'),
    path('verify-ticket/<int:ticket_id>/', views.verify_ticket_page, name='verify_ticket'),
    path('submit-subscription/', views.submit_subscription_form, name='submit_subscription'),
    path("payment/subscription-callback/", views.wayforpay_subscription_callback, name="wayforpay_subscription_callback"),
    path("payment/subscription-result/", views.subscription_payment_result, name="subscription_payment_result"),
    path("sold-out/", TemplateView.as_view(template_name="sold_out.html"), name="sold_out"),
    path("api/get_order_by_token/", get_order_by_token, name="get_order_by_token"),
    path("api/bot/subscription-by-token/", get_subscription_by_token, name="get_subscription_by_token"),
    path("generate-free-ticket/", views.generate_free_ticket, name="generate_free_ticket"),
    path("api/internal/subscription-orders/<path:order_reference>/",
         views.subscription_order_by_reference, name="subscription_order_by_reference",
    ),

]
