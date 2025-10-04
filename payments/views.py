from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import hmac
import time
import hashlib
import json
from .keycrm_api import KeyCRMAPI
from .forms import TicketOrderForm
import logging
from django.shortcuts import render
from .models import TicketOrder
import qrcode
from io import BytesIO
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'index.html')


def mobile(request):
    return render(request, 'mobile.html')


def generate_wayforpay_params(order):
    merchant_account = settings.WAYFORPAY_MERCHANT_ACCOUNT
    merchant_domain = settings.WAYFORPAY_DOMAIN.rstrip('/')
    secret_key = settings.WAYFORPAY_SECRET_KEY

    # Унікальний orderReference
    order_reference = f"ORDER_{order.id}_{int(time.time())}"
    order.wayforpay_order_reference = order_reference
    order.save()

    # --- Дані для платежу ---
    amount = float(order.amount)
    params = {
        "merchantAccount": merchant_account,
        "merchantDomainName": merchant_domain,
        "orderReference": order_reference,
        "orderDate": str(int(time.time())),
        "amount": f"{amount:.2f}",
        "currency": "UAH",
        "productName[]": ["PASUE Club - Grand Opening Party Ticket"],
        "productCount[]": ["1"],
        "productPrice[]": [f"{amount:.2f}"],
        "clientEmail": order.email,
        "clientPhone": order.phone,
        "language": "uk",  # UA, EN, AUTO
        "returnUrl": f"{settings.WAYFORPAY_RETURN_URL}?orderReference={order_reference}",
        "serviceUrl": settings.WAYFORPAY_SERVICE_URL,
    }

    # --- Формуємо підпис ---
    signature_string = ";".join([
        params["merchantAccount"],
        params["merchantDomainName"],
        params["orderReference"],
        params["orderDate"],
        params["amount"],
        params["currency"],
        *params["productName[]"],
        *params["productCount[]"],
        *params["productPrice[]"],
    ])

    merchant_signature = hmac.new(
        secret_key.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest()

    params["merchantSignature"] = merchant_signature

    return params


def build_keycrm_lead(order, status="not_paid", comment=""):
    return {
        "title": f"Замовлення №{order.id}",
        "pipeline_id": settings.KEYCRM_PIPELINE_ID,
        "source_id": settings.KEYCRM_SOURCE_ID,
        "contact": {
            "full_name": order.email or "Без імені",
            "email": order.email,
            "phone": order.phone
        },
        "payments": [
            {
                "payment_method": "WayForPay",
                "amount": float(order.amount),
                "status": status  # "not_paid", "paid", "declined"
            }
        ],
        "manager_comment": comment or f"Статус оплати: {status}",
        "custom_fields": [
            {
                "uuid": "device_type",
                "value": order.device_type
            },
            {
                "uuid": "order_id",
                "value": str(order.id)
            }
        ]
    }


@csrf_exempt
def submit_ticket_form(request):
    if request.method == "POST":
        form = TicketOrderForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]

            ua_string = request.META.get("HTTP_USER_AGENT", "").lower()
            device_type = "mobile" if "mobi" in ua_string else "desktop"

            # Створюємо замовлення
            order = TicketOrder.objects.create(
                email=email,
                phone=phone,
                payment_status="pending",
                amount=1.00,
                device_type=device_type,
            )

            # Створюємо лід в KeyCRM
            if settings.KEYCRM_API_TOKEN and settings.KEYCRM_PIPELINE_ID and settings.KEYCRM_SOURCE_ID:
                try:
                    keycrm = KeyCRMAPI()

                    lead_data = {
                        "title": f"Замовлення #{order.id}",
                        "pipeline_id": settings.KEYCRM_PIPELINE_ID,
                        "source_id": settings.KEYCRM_SOURCE_ID,
                        "manager_comment": "Лендінг: Grand Opening Party",
                        "contact": {
                            "email": email,
                            "phone": phone
                        },
                        "products": [
                            {
                                "sku": f"ticket-{order.id}",
                                "price": float(order.amount),
                                "quantity": 1,
                                "unit_type": "шт",
                                "name": "Квиток на Grand Opening Party",
                            }
                        ],
                        "payments": [
                            {
                                "payment_method": "WayForPay",
                                "amount": float(order.amount),
                                "description": "Очікування оплати",
                                "status": "not_paid"
                            }
                        ],
                        "custom_fields": [
                            {"uuid": "device_type", "value": device_type},
                            {"uuid": "order_id", "value": str(order.id)}
                        ]
                    }

                    lead = keycrm.create_lead(lead_data)

                    if lead and 'id' in lead:
                        order.keycrm_lead_id = lead['id']
                        order.save()
                        logger.info(f"Лід {lead['id']} створено для замовлення {order.id}")
                    else:
                        logger.warning(f"Не вдалося створити лід в KeyCRM для замовлення {order.id}")

                except Exception as e:
                    logger.error(f"Помилка при створенні ліда в KeyCRM: {str(e)}")

            # Генеруємо параметри для оплати
            params = generate_wayforpay_params(order)
            return JsonResponse({"success": True, "wayforpay_params": params})

        else:
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)

    return JsonResponse({"success": False}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def wayforpay_callback(request):
    """Webhook від WayForPay"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        logger.info("=== CALLBACK DATA ===")
        logger.info(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("=== END CALLBACK DATA ===")

        order_reference = data.get("orderReference")
        transaction_status = data.get("transactionStatus")
        merchant_signature = data.get("merchantSignature")

        if not order_reference:
            return HttpResponse("Missing orderReference", status=400)

        try:
            order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)
            logger.info(f"KeyCRM lead id: {order.keycrm_lead_id}")
        except TicketOrder.DoesNotExist:
            logger.info(f"Order not found: {order_reference}")
            return HttpResponse("Order not found", status=404)

        # Формуємо підпис для перевірки
        signature_fields = [
            data.get("merchantAccount", ""),
            data.get("orderReference", ""),
            str(data.get("amount", "")),
            data.get("currency", ""),
            str(data.get("authCode", "")),
            data.get("cardPan", ""),
            str(data.get("transactionStatus", "")),
            str(data.get("reasonCode", "")),
        ]
        signature_string = ";".join(signature_fields)
        expected_signature = hmac.new(
            settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.md5
        ).hexdigest()

        logger.info("=== CALLBACK SIGNATURE DEBUG ===")
        logger.info(f"Signature fields: {signature_fields}")
        logger.info(f"Signature string: {signature_string}")
        logger.info(f"Expected signature: {expected_signature}")
        logger.info(f"Received signature: {merchant_signature}")

        if expected_signature != merchant_signature:
            logger.info("=== SIGNATURE MISMATCH ===")
            return HttpResponse("Invalid signature", status=403)

        logger.info("=== SIGNATURE VALID ===")

        # Оновлюємо статус замовлення
        if transaction_status == "Approved":
            order.payment_status = "success"
            order.email = data.get("clientEmail", order.email)
            order.phone = data.get("clientPhone", order.phone)
            order.save()

            # Відправка email
            if order.email_status != "sent":
                try:
                    send_confirmation_email(order)
                    logger.info(f"Email sent for order {order_reference}")
                except Exception as e:
                    logger.error(f"Email sending error for order {order_reference}: {e}")
            else:
                logger.info(f"Email already sent for order {order_reference}, skipping.")
        else:
            order.payment_status = "failed"
            order.save()

        # --- Підтвердження для WayForPay (для будь-якого статусу) ---
        status = "accept"
        ts = int(time.time())
        sig_source = f"{order_reference};{status};{settings.WAYFORPAY_SECRET_KEY}"

        response_signature = hmac.new(
            settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
            sig_source.encode("utf-8"),
            hashlib.md5
        ).hexdigest()

        response_data = {
            "orderReference": order_reference,
            "status": status,
            "time": ts,
            "signature": response_signature,
        }

        return JsonResponse(response_data, status=200)

    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=400)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def payment_result(request):
    order_reference = request.GET.get("orderReference")
    order = None
    status = "failed"

    if order_reference:
        try:
            order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)
            status = "success" if order.payment_status == "success" else "failed"
        except TicketOrder.DoesNotExist:
            order = None
            status = "failed"

    template = "payment_success.html" if status == "success" else "payment_failed.html"
    return render(request, template, {"order": order})


def send_confirmation_email(order):
    """Відправка email після успішної оплати"""
    # try:
    #     subject = 'PASUE Club - Підтвердження оплати квитка'
    #     message = f"""
    #     Вітаємо!
    #
    #     Ваш квиток на Grand Opening Party від PASUE Club успішно оплачено.
    #
    #     Деталі замовлення:
    #     Email: {order.email}
    #     Телефон: {order.phone}
    #     Номер замовлення: {order.wayforpay_order_reference}
    #     Сума: {order.amount} UAH
    #
    #     Дякуємо за покупку!
    #     Команда PASUE Club
    #     """
    #
    #     send_mail(
    #         subject,
    #         message,
    #         settings.DEFAULT_FROM_EMAIL,
    #         [order.email],
    #         fail_silently=False,
    #     )
    #     order.email_status = 'sent'
    # except Exception as e:
    #     print(f"Email sending error: {str(e)}")
    #     order.email_status = 'failed'
    #
    # order.save()
    qr = qrcode.make(f"TICKET-{order.id}-{order.email}")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_bytes = buffer.getvalue()

    subject = f"Ваш квиток на {order.event_name}"
    html_content = render_to_string("emails/ticket.html", {"order": order})

    email = EmailMultiAlternatives(
        subject=subject,
        body="Ваш квиток у вкладенні.",
        from_email="info@pasue.com.ua",
        to=[order.email],
    )
    email.attach_alternative(html_content, "text/html")

    # Додаємо QR-код у вигляді inline-елемента
    qr_image = MIMEImage(qr_bytes)
    qr_image.add_header("Content-ID", "<qrcode.png>")
    qr_image.add_header("Content-Disposition", "inline", filename="qrcode.png")
    email.attach(qr_image)

    email.send(fail_silently=False)


# Допоміжна функція для налаштування KeyCRM
@require_http_methods(["GET"])
def keycrm_info(request):
    """
    Допоміжна функція для отримання ID воронки та джерел
    Викликайте один раз для налаштування
    """
    if not settings.KEYCRM_API_TOKEN:
        return JsonResponse({
            'error': 'KeyCRM API токен не налаштований'
        }, status=400)

    keycrm = KeyCRMAPI()

    pipelines = keycrm.get_pipelines()
    sources = keycrm.get_sources()

    return JsonResponse({
        'pipelines': pipelines,
        'sources': sources
    })
