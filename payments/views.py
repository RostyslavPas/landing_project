from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
import hmac
import time
import hashlib
import json
from .models import TicketOrder
from .forms import TicketOrderForm


def index(request):
    return render(request, 'index.html')


def mobile(request):
    return render(request, 'mobile.html')


@require_http_methods(["POST"])
def submit_ticket_form(request):
    """Форма замовлення квитка"""
    form = TicketOrderForm(request.POST)

    if form.is_valid():
        email = form.cleaned_data['email']
        phone = form.cleaned_data['phone']

        order, _ = TicketOrder.objects.get_or_create(
            email=email,
            defaults={
                'phone': phone,
                'device_type': 'desktop',
                'payment_status': 'pending',
            },
        )

        # генеруємо orderReference
        order_reference = f"ORDER_{order.id}_{int(time.time())}"
        order.wayforpay_order_reference = order_reference
        order.save()

        params = generate_wayforpay_params(order)
        return JsonResponse({"success": True, "wayforpay_params": params})

    return JsonResponse({"success": False, "errors": form.errors})


def generate_wayforpay_params(order):
    """Генерація параметрів для WayForPay з коректним підписом"""
    merchant_account = settings.WAYFORPAY_MERCHANT_ACCOUNT
    merchant_secret_key = settings.WAYFORPAY_SECRET_KEY
    merchant_domain = settings.WAYFORPAY_DOMAIN.rstrip('/')

    order_reference = f"ORDER_{order.id}_{int(time.time())}"
    order.wayforpay_order_reference = order_reference
    order.save()

    # Форматування суми з двома знаками після коми
    amount_float = float(order.amount)

    params = {
        "merchantAccount": merchant_account,
        "merchantDomainName": merchant_domain,  # без https://
        "orderReference": order_reference,
        "orderDate": int(time.time()),
        "amount": f"{amount_float:.2f}",
        "currency": "UAH",
        "productName[]": ["PASUE Club - Grand Opening Party Ticket"],
        "productCount[]": [str(1)],
        "productPrice[]": [amount_float],
        "clientFirstName": "Client",
        "clientLastName": "Name",
        "clientEmail": order.email,
        "clientPhone": order.phone,
        "language": "uk",
        "returnUrl": settings.WAYFORPAY_RETURN_URL,
        "serviceUrl": settings.WAYFORPAY_SERVICE_URL,
    }

    # Формування підпису (md5)
    signature_string = ";".join([
        params["merchantAccount"],
        params["merchantDomainName"],
        params["orderReference"],
        str(params["orderDate"]),
        params["amount"],
        params["currency"],
        *params["productName[]"],
        *[str(c) for c in params["productCount[]"]],
        *[f"{p:.2f}" for p in params["productPrice[]"]],
    ])

    full_signature_string = f"{signature_string};{merchant_secret_key}"
    signature = hashlib.md5(full_signature_string.encode("utf-8")).hexdigest()
    params["merchantSignature"] = signature

    # Дебаг
    print("=== WAYFORPAY INIT DEBUG ===")
    print(f"Signature string: {signature_string}")
    print(f"Full string with key: {full_signature_string}")
    print(f"Generated signature: {signature}")
    print("=== END DEBUG ===")

    return params


@csrf_exempt
@require_http_methods(["POST"])
def wayforpay_callback(request):
    """Webhook від WayForPay"""
    try:
        data = json.loads(request.body.decode("utf-8"))

        order_reference = data.get("orderReference")
        transaction_status = data.get("transactionStatus")
        merchant_signature = data.get("merchantSignature")

        if not order_reference:
            return HttpResponse("Missing orderReference", status=400)

        try:
            order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)
        except TicketOrder.DoesNotExist:
            return HttpResponse("Order not found", status=404)

        # Порядок полів для callback згідно документації
        signature_fields = [
            data.get("merchantAccount", ""),
            data.get("orderReference", ""),
            str(data.get("amount", "")),
            data.get("currency", ""),
            str(data.get("authCode", "")),
            data.get("cardPan", ""),
            data.get("transactionStatus", ""),
            str(data.get("reasonCode", "")),
        ]

        signature_string = ";".join(signature_fields)
        full_signature_string = f"{signature_string};{settings.WAYFORPAY_SECRET_KEY}"
        expected_signature = hashlib.md5(full_signature_string.encode("utf-8")).hexdigest()

        if expected_signature != merchant_signature:
            print("=== WAYFORPAY CALLBACK SIGNATURE ERROR ===")
            print(f"Signature string: {signature_string}")
            print(f"Full string with key: {full_signature_string}")
            print(f"Expected signature: {expected_signature}")
            print(f"Received signature: {merchant_signature}")
            print("=== END DEBUG ===")
            return HttpResponse("Invalid signature", status=403)

        # оновлюємо статус
        if transaction_status == "Approved":
            order.payment_status = "success"
            order.save()
            send_confirmation_email(order)
        else:
            order.payment_status = "failed"
            order.save()

        return JsonResponse({"orderReference": order_reference, "status": "accept"}, status=200)

    except Exception as e:
        print(f"Callback error: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=400)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def payment_success(request):
    """Сторінка успішної оплати"""
    order_reference = request.GET.get("orderReference")
    order = None
    if order_reference:
        try:
            order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)
        except TicketOrder.DoesNotExist:
            pass
    return render(request, "payment_success.html", {"order": order})


def payment_failed(request):
    return render(request, "payment_failed.html")


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
    except Exception:
        order.email_status = 'failed'

    order.save()