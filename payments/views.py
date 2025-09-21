from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
import json
import hashlib
import time
from .models import TicketOrder
from .forms import TicketOrderForm


def index(request):
    return render(request, 'index.html')


def mobile(request):
    return render(request, 'mobile.html')


@require_http_methods(["POST"])
def submit_ticket_form(request):
    form = TicketOrderForm(request.POST)

    # Визначення типу пристрою
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    is_mobile = any(device in user_agent.lower() for device in
                    ['mobile', 'android', 'iphone', 'ipad'])
    device_type = 'mobile' if is_mobile else 'desktop'

    if form.is_valid():
        email = form.cleaned_data['email']
        phone = form.cleaned_data['phone']

        # Перевіряємо чи існує вже такий користувач
        order, created = TicketOrder.objects.get_or_create(
            email=email,
            defaults={
                'phone': phone,
                'device_type': device_type,
                'payment_status': 'pending'
            }
        )

        if not created:
            # Якщо користувач вже існує, оновлюємо його дані
            order.phone = phone
            order.device_type = device_type
            order.payment_status = 'pending'
            order.save()

        # Генерація параметрів для WayForPay
        wayforpay_params = generate_wayforpay_params(order)

        return JsonResponse({
            'success': True,
            'wayforpay_params': wayforpay_params
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


def generate_wayforpay_params(order):
    """Генерація параметрів для WayForPay"""
    merchant_account = settings.WAYFORPAY_MERCHANT_ACCOUNT
    merchant_secret_key = settings.WAYFORPAY_SECRET_KEY

    order_reference = f"ORDER_{order.id}_{int(time.time())}"
    order.wayforpay_order_reference = order_reference
    order.save()

    params = {
        'merchantAccount': merchant_account,
        'merchantDomainName': settings.WAYFORPAY_DOMAIN,
        'orderReference': order_reference,
        'orderDate': int(time.time()),
        'amount': float(order.amount),
        'currency': 'UAH',
        'productName': ['PASUE Club - Grand Opening Party Ticket'],
        'productCount': [1],
        'productPrice': [float(order.amount)],
        'clientFirstName': 'Client',
        'clientLastName': 'Name',
        'clientEmail': order.email,
        'clientPhone': order.phone,
        'language': 'uk',
        'returnUrl': settings.WAYFORPAY_RETURN_URL,
        'serviceUrl': settings.WAYFORPAY_SERVICE_URL,
    }

    # Генерація підпису
    signature_string = ";".join([
        merchant_account,
        str(params['merchantDomainName']),
        str(params['orderReference']),
        str(params['orderDate']),
        str(params['amount']),
        str(params['currency']),
        str(params['productName'][0]),
        str(params['productCount'][0]),
        str(params['productPrice'][0])
    ])

    params['merchantSignature'] = hashlib.md5(
        f"{signature_string};{merchant_secret_key}".encode('utf-8')
    ).hexdigest()

    return params


@csrf_exempt
@require_http_methods(["POST"])
def wayforpay_callback(request):
    """Обробка callback від WayForPay"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        order_reference = data.get('orderReference')
        transaction_status = data.get('transactionStatus')

        if order_reference:
            try:
                order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)

                if transaction_status == 'Approved':
                    order.payment_status = 'success'
                    order.save()

                    # Відправка email після успішної оплати
                    send_confirmation_email(order)

                elif transaction_status in ['Declined', 'Expired', 'Refunded']:
                    order.payment_status = 'failed'
                    order.save()

                return HttpResponse('OK', status=200)
            except TicketOrder.DoesNotExist:
                return HttpResponse('Order not found', status=404)

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)

    return HttpResponse('Invalid request', status=400)


def payment_success(request):
    """Сторінка успішної оплати"""
    order_reference = request.GET.get('orderReference')
    if order_reference:
        try:
            order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)
            return render(request, 'payment_success.html', {'order': order})
        except TicketOrder.DoesNotExist:
            pass

    return render(request, 'payment_success.html')


def payment_failed(request):
    """Сторінка неуспішної оплати"""
    return render(request, 'payment_failed.html')


def send_confirmation_email(order):
    """Відправка email після успішної оплати"""
    try:
        subject = 'PASUE Club - Підтвердження оплати квитка'
        message = f"""
        Вітаємо!

        Ваш квиток на Grand Opening Party від PASUE Club успішно оплачено.

        Деталі замовлення:
        Email: {order.email}
        Телефон: {order.phone}
        Номер замовлення: {order.wayforpay_order_reference}
        Сума: {order.amount} UAH

        Дякуємо за покупку!
        Команда PASUE Club
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
            fail_silently=False,
        )

        order.email_status = 'sent'
        order.save()

    except Exception as e:
        order.email_status = 'failed'
        order.save()