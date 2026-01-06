import os
import uuid
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import hmac
import time
import hashlib
import json
from urllib.parse import urlencode
from .keycrm_api import KeyCRMAPI
from .forms import TicketOrderForm, SubscriptionOrderForm
import logging
from django.shortcuts import render
from .models import TicketOrder, SubscriptionOrder, Event, Subscription
from .ticket_utils import send_ticket_email_with_pdf
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import BotAccessToken, SubscriptionBotAccessToken
from functools import wraps
from django.views.decorators.http import require_GET
import requests


logger = logging.getLogger(__name__)


def is_staff(user):
    return user.is_staff


def index(request):
    return render(request, 'index.html')


def mobile(request):
    return render(request, 'mobile.html')


# def opening(request):
#     """Сторінка Grand Opening Party (колишня index)"""
#     return render(request, "opening.html")


# def opening_mobile(request):
#     """Мобільна сторінка Grand Opening Party (колишня mobile)"""
#     return render(request, "opening_mobile.html")


def subscription(request):
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

    # перевірка на мобільні пристрої
    is_mobile = any(keyword in user_agent for keyword in [
        "iphone", "android", "mobile", "ipad", "ipod", "opera mini", "blackberry"
    ])

    if is_mobile:
        template_name = "subscription_mobile.html"
    else:
        template_name = "subscription.html"

    return render(request, template_name)


def generate_wayforpay_params(order, product_name=None):
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
        "productName[]": [product_name or "Квиток PASUE Club"],
        "productCount[]": ["1"],
        "productPrice[]": [f"{amount:.2f}"],
        "clientFirstName": order.name,
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
            "full_name": order.name,
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
    utm_source = request.POST.get("utm_source") or request.COOKIES.get("utm_source", "")
    utm_medium = request.POST.get("utm_medium") or request.COOKIES.get("utm_medium", "")
    utm_campaign = request.POST.get("utm_campaign") or request.COOKIES.get("utm_campaign", "")
    utm_term = request.POST.get("utm_term") or request.COOKIES.get("utm_term", "")
    utm_content = request.POST.get("utm_content") or request.COOKIES.get("utm_content", "")
    
    if request.method == "POST":
        form = TicketOrderForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]

            ua_string = request.META.get("HTTP_USER_AGENT", "").lower()
            device_type = "mobile" if "mobi" in ua_string else "desktop"

            # === Перевірка ліміту квитків ===
            with transaction.atomic():
                # Отримуємо активну подію з блокуванням запису
                event = Event.objects.select_for_update().filter(is_active=True).first()
                if not event:
                    return JsonResponse({"success": False, "error": "Подію не знайдено."}, status=400)

                # --- Перевірка промокоду ---
                promo_code_value = form.cleaned_data.get("promo_code", "").strip().upper()

                if promo_code_value == settings.PROMO_CODE:
                    discount_percent = settings.PROMO_DISCOUNT
                    logger.info(f"🎟️ Промокод {promo_code_value} застосовано — {discount_percent}% знижка")
                elif promo_code_value:
                    discount_percent = 0
                    logger.warning(f"❌ Промокод {promo_code_value} недійсний")
                else:
                    discount_percent = 0

                # --- Розрахунок фінальної суми з урахуванням промокоду ---
                base_price = event.price
                final_amount = (base_price * (Decimal(1) - Decimal(discount_percent) / Decimal(100))).quantize(
                    Decimal("0.01"))

                # ⏳ Задаємо ліміт часу для броні (наприклад, 10 хв)
                expiration_time = timezone.now() - timedelta(minutes=10)

                # оновлюємо старі броні
                expired_count = TicketOrder.objects.filter(
                    payment_status="pending",
                    created_at__lt=expiration_time
                ).update(payment_status="expired")

                if expired_count:
                    logger.info(f"🕓 Автоматично оновлено {expired_count} старих броней у статус 'expired'")

                # 🔥 Рахуємо тільки актуальні квитки (успішні + pending не старші 10 хв)
                active_orders = TicketOrder.objects.filter(
                    event=event,
                    payment_status__in=["success", "pending"],
                ).exclude(
                    payment_status="pending",
                    created_at__lt=expiration_time
                ).count()

                if active_orders >= event.max_tickets:
                    return JsonResponse({"success": False, "redirect_url": "/sold-out/"})

                # Створюємо замовлення
                order = TicketOrder.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    payment_status="pending",
                    amount=final_amount,
                    device_type=device_type,
                    event=event,
                    ticket_number=active_orders + 1
                )

                logger.info(f"📝 Створено замовлення #{order.id} (квиток №{order.ticket_number})")

            # Створюємо лід в KeyCRM з платежем в масиві
            if settings.KEYCRM_API_TOKEN and settings.KEYCRM_PIPELINE_ID and settings.KEYCRM_SOURCE_ID:
                try:
                    keycrm = KeyCRMAPI()

                    lead_data = {
                        "title": f"Замовлення #{order.id}",
                        "pipeline_id": settings.KEYCRM_PIPELINE_ID,
                        "source_id": settings.KEYCRM_SOURCE_ID,
                        "manager_comment": "Лендінг: Grand Opening Party",
                        "contact": {
                            "full_name": name,
                            "email": email,
                            "phone": phone
                        },
                        "utm_source": utm_source,
                        "utm_medium": utm_medium,
                        "utm_campaign": utm_campaign,
                        "utm_term": utm_term,
                        "utm_content": utm_content,
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

                    logger.info(f"🔄 Відправка даних в KeyCRM для замовлення #{order.id}")
                    lead = keycrm.create_pipeline_card(lead_data)

                    if lead and lead.get('id'):
                        order.keycrm_lead_id = lead['id']
                        
                        # Беремо contact_id з відповіді
                        lead_response = lead.get('response', {})
                        if lead_response.get('contact_id'):
                            order.keycrm_contact_id = lead_response['contact_id']
                        
                        # Беремо платежі з відповіді при створенні ліда
                        payments = lead_response.get('payments', [])
                        
                        logger.info(f"🔍 В відповіді при створенні ліда знайдено {len(payments)} платежів")
                        
                        if payments and len(payments) > 0:
                            order.keycrm_payment_id = payments[0].get('id')
                            logger.info(f"💾 Збережено payment_id з відповіді: {order.keycrm_payment_id}")
                        else:
                            logger.warning(f"⚠️ Платежі не знайдено в відповіді при створенні ліда")
                        
                        order.save()
                        logger.info(f"✅ Лід {lead['id']} створено для замовлення {order.id}")
                    else:
                        logger.warning(f"⚠️ Не вдалося створити лід в KeyCRM для замовлення {order.id}")
                        logger.warning(f"Відповідь KeyCRM: {lead}")

                except Exception as e:
                    logger.error(f"❌ Помилка при створенні ліда в KeyCRM: {str(e)}")

            # Додаємо інформацію про квиток у назву продукту
            # order_description = f"{event.title} — Квиток №{order.ticket_number} із {event.max_tickets}"
            order_description = f"{event.title}"

            # Генеруємо параметри для оплати
            params = generate_wayforpay_params(order, product_name=order_description)

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
            logger.info(
                f"Знайдено замовлення #{order.id}, KeyCRM lead id: {order.keycrm_lead_id}, payment id: {order.keycrm_payment_id}")
        except TicketOrder.DoesNotExist:
            logger.info(f"Order not found: {order_reference}")
            return HttpResponse("Order not found", status=404)

        # Перевірка на повторний callback
        if order.callback_processed and order.payment_status == "success":
            logger.info(f"ℹ️ Callback вже оброблено для замовлення #{order.id}")
            status = "accept"
            ts = int(time.time())
            sig_source = f"{order_reference};{status};{settings.WAYFORPAY_SECRET_KEY}"
            response_signature = hmac.new(
                settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
                sig_source.encode("utf-8"),
                hashlib.md5
            ).hexdigest()
            return JsonResponse({
                "orderReference": order_reference,
                "status": status,
                "time": ts,
                "signature": response_signature
            })

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
        logger.info(f"Expected signature: {expected_signature}")
        logger.info(f"Received signature: {merchant_signature}")

        if expected_signature != merchant_signature:
            logger.error("=== SIGNATURE MISMATCH ===")
            return HttpResponse("Invalid signature", status=403)

        logger.info("=== SIGNATURE VALID ===")

        # Оновлюємо статус замовлення
        if transaction_status == "Approved":
            order.payment_status = "success"
            order.callback_processed = True
            order.name = data.get("clientFirstName", order.name)
            order.email = data.get("clientEmail", order.email)
            order.phone = data.get("clientPhone", order.phone)
            order.save()

            logger.info(f"✅ Замовлення #{order.id} позначено як оплачене")

            # Відправка email
            if order.email_status != "sent":
                try:
                    send_ticket_email_with_pdf(order)
                    order.email_status = "sent"
                    order.save(update_fields=["email_status"])
                    logger.info(f"📧 Email відправлено для замовлення #{order.id}")
                except Exception as e:
                    logger.error(f"❌ Помилка відправки email для замовлення #{order.id}: {e}")
            else:
                logger.info(f"ℹ️ Email вже було відправлено для замовлення #{order.id}")

            # === KeyCRM оновлення (ПРАВИЛЬНИЙ ФЛОУ згідно з документацією) ===
            if order.keycrm_lead_id and order.keycrm_payment_id and settings.KEYCRM_API_TOKEN:
                try:
                    keycrm = KeyCRMAPI()

                    logger.info(f"📋 Дані з WayForPay callback:")
                    logger.info(f"   - orderReference: {data.get('orderReference')}")
                    logger.info(f"   - authCode: {data.get('authCode')}")
                    logger.info(f"   - amount: {data.get('amount')}")
                    logger.info(f"   - processingDate: {data.get('processingDate')}")
                    logger.info(f"   - order.id: {order.id}")

                    transaction_attached = False

                    # СТРАТЕГІЯ: Пошук у списку зовнішніх транзакцій з retry
                    # Причина: KeyCRM потрібен час, щоб отримати транзакцію від WayForPay
                    logger.info(f"🔄 Пошук транзакції в списку зовнішніх транзакцій")

                    # Спробуємо знайти транзакцію кілька разів з затримкою
                    max_attempts = 3
                    wait_seconds = [2, 5, 10]  # Затримки між спробами

                    callback_amount = float(data.get('amount', 0))
                    callback_auth_code = data.get('authCode', '')
                    callback_processing_date = data.get('processingDate', 0)

                    for attempt in range(max_attempts):
                        if transaction_attached:
                            break

                        if attempt > 0:
                            wait_time = wait_seconds[attempt - 1]
                            logger.info(f"⏳ Зачекаємо {wait_time} секунд перед спробою #{attempt + 1}")
                            import time as time_module
                            time_module.sleep(wait_time)

                        logger.info(f"🔍 Спроба #{attempt + 1}: Шукаємо транзакцію")

                        # Отримуємо останні транзакції (без фільтра, щоб побачити всі)
                        transactions_result = keycrm.get_external_transactions(limit=100)

                        if transactions_result:
                            transaction_list = transactions_result.get('data', transactions_result) if isinstance(
                                transactions_result, dict) else transactions_result

                            if isinstance(transaction_list, list) and len(transaction_list) > 0:
                                logger.info(f"📦 Отримано {len(transaction_list)} транзакцій для аналізу")

                                # Шукаємо транзакцію за точною відповідністю
                                matching_transaction = None

                                for trans in transaction_list:
                                    trans_id = trans.get('id')
                                    trans_desc = trans.get('description', '')
                                    trans_amount = float(trans.get('amount', 0))
                                    trans_uuid = trans.get('uuid', '')
                                    trans_created = trans.get('created_at', '')

                                    # Критерії для точної відповідності:
                                    # 1. Сума збігається
                                    # 2. AuthCode або orderReference згадується в description або uuid
                                    matches_amount = abs(trans_amount - callback_amount) < 0.01
                                    matches_auth_code = callback_auth_code and callback_auth_code in trans_desc
                                    matches_order_ref = order.wayforpay_order_reference in trans_desc or order.wayforpay_order_reference in trans_uuid
                                    matches_order_id = f"#{order.id}" in trans_desc or f"#{order.id} " in trans_desc

                                    logger.info(f"   🔍 Перевірка транзакції ID: {trans_id}")
                                    logger.info(f"      - Description: {trans_desc[:100]}")
                                    logger.info(f"      - Amount: {trans_amount} (потрібно: {callback_amount})")
                                    logger.info(f"      - UUID: {trans_uuid}")
                                    logger.info(
                                        f"      - Matches: amount={matches_amount}, auth={matches_auth_code}, order_ref={matches_order_ref}, order_id={matches_order_id}")

                                    # Якщо знайшли точну відповідність
                                    if matches_amount and (matches_auth_code or matches_order_ref):
                                        matching_transaction = trans
                                        logger.info(f"✅ ЗНАЙДЕНО ВІДПОВІДНУ ТРАНЗАКЦІЮ!")
                                        break

                                    # Якщо є лише по order.id - це може бути менш надійно
                                    elif matches_amount and matches_order_id and not matching_transaction:
                                        matching_transaction = trans
                                        logger.info(f"⚠️ Знайдено можливу відповідність по order.id (менш надійно)")

                                if matching_transaction:
                                    transaction_id = matching_transaction.get('id')
                                    logger.info(f"🎯 Використовуємо транзакцію ID: {transaction_id}")

                                    # Прив'язуємо транзакцію
                                    attach_result = keycrm.attach_external_transaction_by_id(
                                        payment_id=order.keycrm_payment_id,
                                        transaction_id=transaction_id
                                    )

                                    if attach_result:
                                        logger.info(
                                            f"✅ Транзакцію {transaction_id} успішно прив'язано до платежу {order.keycrm_payment_id}")
                                        transaction_attached = True
                                        break
                                    else:
                                        logger.warning(f"⚠️ Не вдалося прив'язати транзакцію {transaction_id}")
                                else:
                                    logger.warning(f"⚠️ Відповідну транзакцію не знайдено в спробі #{attempt + 1}")

                    # Якщо після всіх спроб транзакцію не знайдено - оновлюємо статус вручну
                    if not transaction_attached:
                        logger.warning(f"⚠️ Зовнішню транзакцію не знайдено після {max_attempts} спроб")
                        logger.info(f"🔄 Оновлення статусу платежу вручну")

                        payment_description = f"Замовлення #{order.wayforpay_order_reference}. Клієнт: {order.name}, {order.phone}, {order.email}. AuthCode: {callback_auth_code}"

                        manual_update = keycrm.update_lead_payment_status(
                            lead_id=order.keycrm_lead_id,
                            payment_id=order.keycrm_payment_id,
                            status="paid",
                            description=payment_description
                        )

                        if manual_update:
                            logger.info(f"✅ Статус платежу {order.keycrm_payment_id} оновлено вручну на 'paid'")
                        else:
                            logger.error(f"❌ Не вдалося оновити статус платежу вручну")
                    else:
                        logger.info(f"🎉 Транзакцію успішно прив'язано! Статус платежу автоматично оновлений в KeyCRM")

                except Exception as e:
                    logger.error(f"❌ Помилка при роботі з KeyCRM: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")

            else:
                if not order.keycrm_payment_id:
                    logger.warning(f"⚠️ KeyCRM payment_id відсутній для замовлення #{order.id}")
                if not settings.KEYCRM_API_TOKEN:
                    logger.warning(f"⚠️ KEYCRM_API_TOKEN не налаштований")

        elif transaction_status == "Declined":
            order.payment_status = "failed"
            order.callback_processed = True
            order.save()
            logger.info(f"❌ Оплата відхилена для замовлення #{order.id}")

        else:
            order.payment_status = "failed"
            order.callback_processed = True
            order.save()
            logger.info(f"⚠️ Невідомий статус транзакції: {transaction_status}")

        # Підтвердження для WayForPay
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
        logger.error(f"❌ Callback error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    try:
        send_ticket_email_with_pdf(order)
        order.email_status = 'sent'
        order.save(update_fields=["email_status"])
        logger.info(f"Email з PDF відправлено для замовлення {order.id}")
    except Exception as e:
        logger.error(f"Помилка відправки email: {str(e)}")
        order.email_status = 'failed'
        order.save(update_fields=["email_status"])


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


@csrf_exempt
@require_http_methods(["GET"])
def validate_ticket_api(request, ticket_id):
    """API для перевірки статусу квитка"""
    try:
        ticket = TicketOrder.objects.get(id=ticket_id, payment_status='success')
        return JsonResponse({
            'success': True,
            'order_id': ticket.id,
            'event_name': ticket.event_name,
            'status': ticket.ticket_status,
            'is_valid': ticket.is_valid(),
            'scan_count': ticket.scan_count,
        })
    except TicketOrder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Квиток не знайдено'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def scan_ticket_api(request, ticket_id):
    """API для сканування квитка - АВТОМАТИЧНО підтверджує та змінює статус"""
    try:
        ticket = TicketOrder.objects.get(id=ticket_id, payment_status='success')

        body = json.loads(request.body) if request.body else {}
        scanned_by = body.get('scanned_by', 'scanner')

        was_valid = ticket.is_valid()
        previous_status = ticket.ticket_status

        # Логування
        from .models import TicketScanLog
        TicketScanLog.objects.create(
            ticket=ticket,
            scanned_by=scanned_by,
            ip_address=request.META.get('REMOTE_ADDR'),
            was_valid=was_valid,
            previous_status=ticket.ticket_status
        )

        # АВТОМАТИЧНО ПІДТВЕРДЖУЄМО при скануванні через сканер
        if was_valid:
            # Відмічаємо як використаний
            ticket.mark_as_used(scanned_by=scanned_by)

            # Якщо є авторизований користувач, зберігаємо його
            if hasattr(request, 'user') and request.user.is_authenticated:
                ticket.verify_ticket(request.user)
            else:
                # Якщо немає user, просто відмічаємо як verified
                from django.utils import timezone
                ticket.is_verified = True
                ticket.verified_at = timezone.now()
                ticket.save()

            message = '✅ Квиток дійсний! Вхід дозволено.'
            status_type = 'valid'
        elif ticket.ticket_status == 'used':
            message = '⚠️ Квиток вже був використаний.'
            status_type = 'used'
        else:
            message = '❌ Квиток недійсний.'
            status_type = 'invalid'

        return JsonResponse({
            'success': True,
            'order_id': ticket.id,
            'event_name': ticket.event_name,
            'was_valid': was_valid,
            'status': ticket.ticket_status,
            'is_verified': ticket.is_verified,
            'scan_count': ticket.scan_count,
            'message': message,
            'status_type': status_type
        })
    except TicketOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Квиток не знайдено',
            'status_type': 'invalid'
        }, status=404)


def scanner_page(request):
    """Сторінка сканера"""
    return render(request, 'scanner.html')


def verify_ticket_page(request, ticket_id):
    """Сторінка перевірки квитка по QR-коду"""
    try:
        ticket = TicketOrder.objects.get(id=ticket_id, payment_status='success')

        context = {
            'ticket': ticket,
            'is_valid': ticket.is_valid(),
            'status_text': {
                'active': 'Дійсний',
                'used': 'Використаний',
                'invalid': 'Недійсний'
            }.get(ticket.ticket_status, 'Невідомо')
        }

        return render(request, 'verify_ticket.html', context)

    except TicketOrder.DoesNotExist:
        return render(request, 'verify_ticket.html', {
            'ticket': None,
            'error': 'Квиток не знайдено'
        })


def find_subscription_by_callback(order_reference, client_email, client_phone):
    """
    Знаходить підписку за різними критеріями по черзі.
    Повертає підписку або None.
    """
    subscription = None

    # 1. Пошук за order_reference (якщо він був збережений раніше)
    if order_reference:
        try:
            subscription = SubscriptionOrder.objects.get(
                wayforpay_order_reference=order_reference
            )
            logger.info(f"✅ Знайдено підписку #{subscription.id} за order_reference")
            return subscription
        except SubscriptionOrder.DoesNotExist:
            logger.info(f"⚠️ Підписку за order_reference '{order_reference}' не знайдено")

    # 2. ✅ ГОЛОВНЕ: Пошук за email + phone (найнадійніший для кнопки)
    if client_email and client_phone:
        # Нормалізуємо телефон (видаляємо всі символи крім цифр)
        phone_digits = ''.join(filter(str.isdigit, client_phone))

        # Шукаємо за email та останніми 9 цифрами телефону
        subscriptions = SubscriptionOrder.objects.filter(
            email=client_email,
            payment_status='pending',
            callback_processed=False
        ).order_by('-created_at')

        for sub in subscriptions:
            sub_phone_digits = ''.join(filter(str.isdigit, sub.phone))
            # Порівнюємо останні 9 цифр (без коду країни)
            if phone_digits[-9:] == sub_phone_digits[-9:]:
                logger.info(f"✅ Знайдено підписку #{sub.id} за email+phone")
                sub.wayforpay_order_reference = order_reference
                sub.save()
                return sub

    # 3. Пошук за часом створення (якщо email не збігся, але час недавній)
    from django.utils import timezone
    from datetime import timedelta

    if client_email or client_phone:
        time_threshold = timezone.now() - timedelta(minutes=5)  # Збільшено до 15 хв

        recent_subscriptions = SubscriptionOrder.objects.filter(
            payment_status='pending',
            callback_processed=False,
            created_at__gte=time_threshold
        ).order_by('-created_at')

        logger.info(f"🔍 Знайдено {recent_subscriptions.count()} недавніх підписок")

        for sub in recent_subscriptions:
            # Порівнюємо email (case-insensitive)
            email_match = client_email and sub.email.lower() == client_email.lower()

            # Порівнюємо телефони (останні 9 цифр)
            phone_match = False
            if client_phone:
                client_phone_digits = ''.join(filter(str.isdigit, client_phone))
                sub_phone_digits = ''.join(filter(str.isdigit, sub.phone))
                phone_match = client_phone_digits[-9:] == sub_phone_digits[-9:]

            if email_match or phone_match:
                logger.info(f"✅ Знайдено підписку #{sub.id} за часом створення (email={email_match}, phone={phone_match})")
                sub.wayforpay_order_reference = order_reference
                sub.save()
                return sub

    # 4. Останній варіант: якщо є лише 1 незавершена підписка за останні 15 хв
    recent_single = SubscriptionOrder.objects.filter(
        payment_status='pending',
        callback_processed=False,
        created_at__gte=timezone.now() - timedelta(minutes=5)
    ).order_by('-created_at').first()

    if recent_single:
        logger.warning(f"⚠️ Використано резервний варіант: підписка #{recent_single.id}")
        recent_single.wayforpay_order_reference = order_reference
        recent_single.save()
        return recent_single

    return None


def update_keycrm_payment(subscription, wfp_data):
    """
    Оновлює платіж у KeyCRM після успішної транзакції WayForPay.
    Працює з автоматичним пошуком транзакції та ручним апдейтом, якщо не знайдено.
    """
    if not (subscription.keycrm_lead_id and subscription.keycrm_payment_id and settings.KEYCRM_API_TOKEN):
        logger.warning(f"⚠️ Відсутні дані для KeyCRM: lead_id={subscription.keycrm_lead_id}, payment_id={subscription.keycrm_payment_id}")
        return

    keycrm = KeyCRMAPI()
    callback_auth_code = wfp_data.get("authCode", "")
    order_reference = wfp_data.get("orderReference", "")

    logger.warning(f"⚠️Оновлюємо транзакцію вручну.")
    payment_description = (
        f"Підписка #{order_reference}. "
        f"Клієнт: {subscription.name or ''}, {subscription.phone or ''}, {subscription.email or ''}. "
        f"AuthCode: {callback_auth_code}"
    )
    manual_update = keycrm.update_lead_payment_status(
        lead_id=subscription.keycrm_lead_id,
        payment_id=subscription.keycrm_payment_id,
        status="paid",
        description=payment_description
    )
    if manual_update:
        logger.info(f"✅ Статус платежу {subscription.keycrm_payment_id} оновлено вручну на 'paid'")
    else:
        logger.error(f"❌ Не вдалось оновити статус платежу вручну")


@csrf_exempt
@require_http_methods(["POST"])
def wayforpay_subscription_callback(request):
    """Webhook від WayForPay для підписок"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        logger.info("=== CALLBACK DATA ===")
        logger.info(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("=== END CALLBACK DATA ===")

        order_reference = data.get("orderReference")
        transaction_status = data.get("transactionStatus")
        merchant_signature = data.get("merchantSignature")
        
        # ✅ Отримуємо email та phone з різних можливих полів
        client_email = (
            data.get("clientEmail") or 
            data.get("email") or 
            data.get("client_email") or
            ""
        ).strip().lower()  # Нормалізуємо email
        
        client_phone = (
            data.get("clientPhone") or 
            data.get("phone") or 
            data.get("client_phone") or
            ""
        ).strip()

        logger.info(f"🔍 Пошук підписки:")
        logger.info(f"   - orderReference: {order_reference}")
        logger.info(f"   - email: {client_email}")
        logger.info(f"   - phone: {client_phone}")

        if not order_reference:
            logger.error("❌ Відсутній orderReference у callback")
            return HttpResponse("Missing orderReference", status=400)

        # --- КРИТИЧНО: Знаходимо підписку за різними критеріями ---
        subscription = find_subscription_by_callback(order_reference, client_email, client_phone)

        if not subscription:
            logger.error(f"❌ Підписку не знайдено! order_reference={order_reference}, email={client_email}, phone={client_phone}")
            
            # Додаткова діагностика
            logger.info("📊 Статистика незавершених підписок:")
            pending_subs = SubscriptionOrder.objects.filter(
                payment_status='pending',
                callback_processed=False
            ).order_by('-created_at')[:5]
            
            for sub in pending_subs:
                logger.info(f"   - ID: {sub.id}, Email: {sub.email}, Phone: {sub.phone}, Created: {sub.created_at}")
            
            return HttpResponse("Subscription not found", status=404)

        logger.info(f"✅ Знайдено підписку #{subscription.id}")

        # --- Перевірка на повторний callback ---
        if subscription.callback_processed and subscription.payment_status == "success":
            logger.info(f"ℹ️ Callback вже оброблено для підписки #{subscription.id}")
            status = "accept"
            ts = int(time.time())
            sig_source = f"{order_reference};{status};{settings.WAYFORPAY_SECRET_KEY}"
            response_signature = hmac.new(
                settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
                sig_source.encode("utf-8"),
                hashlib.md5
            ).hexdigest()
            return JsonResponse({
                "orderReference": order_reference,
                "status": status,
                "time": ts,
                "signature": response_signature
            })

        # --- Перевірка підпису WayForPay ---
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

        logger.info(f"🔐 Перевірка підпису:")
        logger.info(f"   Expected: {expected_signature}")
        logger.info(f"   Received: {merchant_signature}")
        
        if expected_signature != merchant_signature:
            logger.error("❌ Підпис не збігається!")
            return HttpResponse("Invalid signature", status=403)
        
        logger.info("✅ Підпис валідний")

        # --- Оновлюємо статус підписки ---
        if transaction_status == "Approved":
            subscription.payment_status = "success"
            subscription.callback_processed = True
            subscription.wayforpay_order_reference = order_reference

            # 🔄 Ім'я та телефон можемо оновити
            if data.get("clientFirstName"):
                subscription.name = data.get("clientFirstName")

            # ❗️Важливо: email НЕ оновлюємо, лишаємо той, що з форми
            if client_email and client_email != subscription.email.lower():
                logger.info(
                    f"ℹ️ Email з WayForPay ({client_email}) "
                    f"відрізняється від email форми ({subscription.email}). "
                    f"Лист буде відправлено на email з форми."
                )

            # ❗️ Телефон також НЕ оновлюємо — залишаємо з форми
            if client_phone:
                form_phone_digits = ''.join(filter(str.isdigit, subscription.phone))
                callback_phone_digits = ''.join(filter(str.isdigit, client_phone))

                if form_phone_digits[-9:] != callback_phone_digits[-9:]:
                    logger.info(
                        f"ℹ️ Телефон з WayForPay ({client_phone}) "
                        f"не збігається з телефоном з форми ({subscription.phone}). "
                        f"Залишаємо телефон із форми."
                    )
            
            subscription.save()
            logger.info(f"✅ Підписка #{subscription.id} позначена як оплачена")

            # Відправка email з підтвердженням
            send_subscription_confirmation_email(subscription)

            # --- Оновлення KeyCRM ---
            update_keycrm_payment(subscription, data)

        elif transaction_status == "Declined":
            subscription.payment_status = "failed"
            subscription.callback_processed = True
            subscription.wayforpay_order_reference = order_reference
            subscription.save()
            logger.info(f"❌ Оплата підписки відхилена #{subscription.id}")
        else:
            subscription.payment_status = "failed"
            subscription.callback_processed = True
            subscription.wayforpay_order_reference = order_reference
            subscription.save()
            logger.info(f"⚠️ Невідомий статус транзакції: {transaction_status}")

        # --- Відправляємо підтвердження WayForPay ---
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
        logger.info(f"✅ Відправка підтвердження WayForPay: {response_data}")
        return JsonResponse(response_data, status=200)

    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return HttpResponse(f"Error: {str(e)}", status=400)


@csrf_exempt
def submit_subscription_form(request):
    if request.method == "POST":
        form = SubscriptionOrderForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]

            utm_source = request.POST.get("utm_source") or request.COOKIES.get("utm_source", "")
            utm_medium = request.POST.get("utm_medium") or request.COOKIES.get("utm_medium", "")
            utm_campaign = request.POST.get("utm_campaign") or request.COOKIES.get("utm_campaign", "")
            utm_term = request.POST.get("utm_term") or request.COOKIES.get("utm_term", "")
            utm_content = request.POST.get("utm_content") or request.COOKIES.get("utm_content", "")

            ua_string = request.META.get("HTTP_USER_AGENT", "").lower()
            device_type = "mobile" if "mobi" in ua_string else "desktop"

            subscription = SubscriptionOrder.objects.create(
                name=name,
                email=email,
                phone=phone,
                payment_status="pending",
                device_type=device_type,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_term=utm_term,
                utm_content=utm_content
            )

            logger.info(f"🎫 Створено замовлення підписки #{subscription.id}")

            if settings.KEYCRM_API_TOKEN and settings.KEYCRM_SUBSCRIPTION_PIPELINE_ID and settings.KEYCRM_SOURCE_ID:
                try:
                    keycrm = KeyCRMAPI()

                    lead_data = {
                        "title": f"Підписка #{subscription.id}",
                        "pipeline_id": settings.KEYCRM_SUBSCRIPTION_PIPELINE_ID,
                        "source_id": settings.KEYCRM_SOURCE_ID,
                        "manager_comment": "Лендінг: Місячна підписка PASUE City",
                        "contact": {
                            "full_name": name,
                            "email": email,
                            "phone": phone
                        },
                        "utm_source": utm_source,
                        "utm_medium": utm_medium,
                        "utm_campaign": utm_campaign,
                        "utm_term": utm_term,
                        "utm_content": utm_content,
                        "products": [
                            {
                                "sku": f"subscription-{subscription.id}",
                                "price": 350.00,
                                "quantity": 1,
                                "unit_type": "шт",
                                "name": "Місячна підписка PASUE City"
                            }
                        ],
                        "payments": [
                            {
                                "payment_method": "WayForPay",
                                "amount": 350.00,
                                "description": "Очікування оплати",
                                "status": "not_paid"
                            }
                        ],
                        "custom_fields": [
                            {"uuid": "device_type", "value": device_type},
                            {"uuid": "subscription_id", "value": str(subscription.id)}
                        ]
                    }

                    logger.info(f"📤 Відправка даних в KeyCRM для підписки #{subscription.id}")
                    lead = keycrm.create_pipeline_card(lead_data)

                    if lead and lead.get('id'):
                        subscription.keycrm_lead_id = lead['id']

                        lead_response = lead.get('response', {})
                        if lead_response.get('contact_id'):
                            subscription.keycrm_contact_id = lead_response['contact_id']

                        payments = lead_response.get('payments', [])

                        logger.info(f"🔍 В відповіді при створенні ліда знайдено {len(payments)} платежів")

                        if payments and len(payments) > 0:
                            subscription.keycrm_payment_id = payments[0].get('id')
                            logger.info(f"💾 Збережено payment_id з відповіді: {subscription.keycrm_payment_id}")
                        else:
                            logger.warning(f"⚠️ Платежі не знайдено в відповіді при створенні ліда")

                        subscription.save()
                        logger.info(f"✅ Ліда {lead['id']} створено для підписки {subscription.id}")
                    else:
                        logger.warning(f"⚠️ Не вдалось створити ліда у KeyCRM для підписки {subscription.id}")
                        logger.warning(f"Відповідь KeyCRM: {lead}")

                except Exception as e:
                    logger.error(f"❌ Помилка при створенні ліда у KeyCRM: {str(e)}")

            return JsonResponse({"success": True, "subscription_id": subscription.id})
        else:
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)

    return JsonResponse({"success": False}, status=405)


def send_subscription_confirmation_email(subscription):
    """Відправка email після успішної оплати підписки"""

    token_obj, _ = SubscriptionBotAccessToken.objects.get_or_create(
        subscription=subscription,
        funnel_tag="subscription-city",
        defaults={"token": uuid.uuid4().hex[:12]},
    )

    bot_url = f"https://t.me/Pasue_club_bot?start=subscribe_{token_obj.token}"

    # TXT
    text_content = render_to_string(
        "emails/subscription_confirmation.txt",
        {"subscription": subscription, "bot_url": bot_url}
    ).strip()

    # HTML
    html_content = render_to_string(
        "emails/subscription_confirmation.html",
        {"subscription": subscription, "bot_url": bot_url}
    )

    try:
        email = EmailMultiAlternatives(
            subject="🎉 Твоя підписка PASUE City активована!",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[subscription.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Email підтвердження підписки відправлено для #{subscription.id}")

    except Exception as e:
        logger.error(f"Помилка відправки email підписки: {str(e)}")
        raise


def subscription_payment_result(request):
    status = request.GET.get("transactionStatus")
    order_reference = request.GET.get("orderReference")

    subscription = None

    # 1) Спочатку шукаємо по orderReference
    if order_reference:
        subscription = (
            SubscriptionOrder.objects
            .filter(wayforpay_order_reference=order_reference)
            .first()
        )

    # 2) Якщо не знайшли — fallback (email або phone з cookies)
    if not subscription:
        email = request.COOKIES.get("last_sub_email")
        phone = request.COOKIES.get("last_sub_phone")

        if email or phone:
            subscription = (
                SubscriptionOrder.objects
                .filter(email=email)
                .order_by('-created_at')
                .first()
            ) or (
                SubscriptionOrder.objects
                .filter(phone=phone)
                .order_by('-created_at')
                .first()
            )

    # 3) Обираємо шаблон
    template_name = (
        "subscriptions/payment_success.html"
        if status in ["Approved", None]
        else "subscriptions/payment_failed.html"
    )

    return render(request, template_name, {
        "order_reference": order_reference,
        "transaction_status": status,
        "subscription": subscription,
    })


@csrf_exempt
def get_subscription_by_token(request):
    """API: отримання даних по токену для Telegram-бота (підписки)"""
    token = request.GET.get("token")
    if not token:
        return JsonResponse({"error": "Missing token"}, status=400)

    try:
        token_obj = (
            SubscriptionBotAccessToken.objects
            .select_related('subscription')
            .get(token=token, is_active=True)
        )
    except SubscriptionBotAccessToken.DoesNotExist:
        return JsonResponse({"error": "Invalid or inactive token"}, status=404)

    sub = token_obj.subscription

    return JsonResponse({
        "subscription_id": sub.id,
        "lead_id": sub.keycrm_lead_id,
        "name": sub.name,
        "email": sub.email,
        "phone": sub.phone,
        "funnel": token_obj.funnel_tag,
        "payment_status": sub.payment_status,
    })


@csrf_exempt
def get_order_by_token(request):
    """API: отримання даних по токену для Telegram-бота"""
    token = request.GET.get("token")
    if not token:
        return JsonResponse({"error": "Missing token"}, status=400)

    try:
        token_obj = BotAccessToken.objects.select_related('order').get(token=token, is_active=True)
        order = token_obj.order
        return JsonResponse({
            "lead_id": order.keycrm_lead_id,
            "name": order.name,
            "email": order.email,
            "phone": order.phone,
            "event": order.event_name,
            "funnel": token_obj.funnel_tag,
            "payment_status": order.payment_status,
            "ticket_status": order.ticket_status,
        })
    except BotAccessToken.DoesNotExist:
        return JsonResponse({"error": "Invalid or inactive token"}, status=404)


@csrf_exempt
def generate_free_ticket(request):
    """
    Створює безкоштовний квиток (без WayForPay), надсилає лист з QR
    і створює ліда в KeyCRM.
    """
    name = request.GET.get("name", "Тест Користувач")
    email = request.GET.get("email", "test@example.com")
    phone = request.GET.get("phone", "+380000000000")

    # опційно — UTM-мітки, якщо будеш передавати їх у лінку
    utm_source = request.GET.get("utm_source", "")
    utm_medium = request.GET.get("utm_medium", "")
    utm_campaign = request.GET.get("utm_campaign", "")
    utm_term = request.GET.get("utm_term", "")
    utm_content = request.GET.get("utm_content", "")

    with transaction.atomic():
        event = Event.objects.filter(is_active=True).first()
        if not event:
            return JsonResponse({"success": False, "error": "Подію не знайдено."}, status=400)

        expiration_time = timezone.now() - timedelta(minutes=10)
        expired_count = TicketOrder.objects.filter(
            payment_status="pending",
            created_at__lt=expiration_time
        ).update(payment_status="expired")

        active_orders = TicketOrder.objects.filter(
            event=event,
            payment_status__in=["success", "pending"],
        ).exclude(
            payment_status="pending",
            created_at__lt=expiration_time
        ).count()

        # 💡 якщо хочеш повністю free — зроби amount = Decimal("0.00")
        amount = event.price  # або Decimal("0.00") для 100% безкоштовного подарунка

        order = TicketOrder.objects.create(
            name=name,
            email=email,
            phone=phone,
            payment_status="success",   # ✅ одразу успішна
            amount=amount,
            device_type="manual",
            event=event,
            ticket_number=active_orders + 1
        )

        logger.info(f"🎟️ Безкоштовний квиток створено #{order.id} для {name}")

        # --- Створюємо ліда в KeyCRM ---
        if settings.KEYCRM_API_TOKEN and settings.KEYCRM_PIPELINE_ID and settings.KEYCRM_SOURCE_ID:
            try:
                keycrm = KeyCRMAPI()

                product_name = f"Безкоштовний квиток на {event.title}"

                lead_data = {
                    "title": f"Безкоштовний квиток #{order.id}",
                    "pipeline_id": settings.KEYCRM_PIPELINE_ID,
                    "source_id": settings.KEYCRM_SOURCE_ID,
                    "manager_comment": "Безкоштовний / подарунковий квиток (створено вручну)",
                    "contact": {
                        "full_name": name,
                        "email": email,
                        "phone": phone
                    },
                    "utm_source": utm_source,
                    "utm_medium": utm_medium,
                    "utm_campaign": utm_campaign,
                    "utm_term": utm_term,
                    "utm_content": utm_content,
                    "products": [
                        {
                            "sku": f"free-ticket-{order.id}",
                            "price": float(order.amount),  # може бути 0.0
                            "quantity": 1,
                            "unit_type": "шт",
                            "name": product_name,
                        }
                    ],
                    "custom_fields": [
                        {"uuid": "device_type", "value": order.device_type},
                        {"uuid": "order_id", "value": str(order.id)},
                        {"uuid": "ticket_type", "value": "free"},
                    ]
                }

                logger.info(f"📤 Відправка даних в KeyCRM для безкоштовного квитка #{order.id}")
                lead = keycrm.create_pipeline_card(lead_data)

                if lead and lead.get("id"):
                    order.keycrm_lead_id = lead["id"]

                    lead_response = lead.get("response", {})

                    if lead_response.get("contact_id"):
                        order.keycrm_contact_id = lead_response["contact_id"]

                    order.save()
                    logger.info(f"✅ Ліда {lead['id']} створено для безкоштовного замовлення {order.id}")
                else:
                    logger.warning(f"⚠️ Не вдалось створити ліда в KeyCRM для безкоштовного замовлення {order.id}")
                    logger.warning(f"Відповідь KeyCRM: {lead}")

            except Exception as e:
                logger.error(f"❌ Помилка при створенні ліда в KeyCRM для безкоштовного квитка: {str(e)}")

    # --- Надсилання квитка на пошту ---
    try:
        send_ticket_email_with_pdf(order)
        order.email_status = "sent"  # ✅ ОНОВЛЮЄМО СТАТУС
        order.save(update_fields=["email_status"])
        logger.info(f"📩 Лист із безкоштовним квитком надіслано на {email}")
    except Exception as e:
        logger.error(f"❌ Помилка при відправці квитка: {e}")

    return JsonResponse({
        "success": True,
        "message": f"Безкоштовний квиток #{order.id} створено, відправлено на {email} і додано в KeyCRM",
        "order_id": order.id,
        "keycrm_lead_id": getattr(order, "keycrm_lead_id", None),
    })


def require_internal_api_key(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        expected = getattr(settings, "INTERNAL_API_KEY", "")
        provided = request.headers.get("X-API-Key") or request.GET.get("api_key")

        if not expected:
            return JsonResponse({"detail": "Server misconfigured: INTERNAL_API_KEY not set"}, status=500)

        if not provided or provided != expected:
            return JsonResponse({"detail": "Unauthorized"}, status=401)

        return view_func(request, *args, **kwargs)

    return _wrapped


@require_GET
@require_internal_api_key
def subscription_order_by_reference(request, order_reference: str):
    order = (
        SubscriptionOrder.objects
        .filter(wayforpay_order_reference=order_reference)
        .values(
            # Контактна інформація
            "id", "name", "email", "phone", "device_type",

            # Статус
            "payment_status", "wayforpay_order_reference",

            # UTM
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",

            # KeyCRM
            "keycrm_lead_id", "keycrm_payment_id", "keycrm_contact_id",

            # Системна інформація
            "created_at", "updated_at", "callback_processed",
        )
        .first()
    )

    if not order:
        return JsonResponse({"detail": "Not found"}, status=404, json_dumps_params={"ensure_ascii": False})

    # (Опційно, але дуже корисно для бота) підтягнути “живий” статус підписки з таблиці Subscription
    sub = (
        Subscription.objects
        .filter(order_reference=order_reference)
        .values(
            "status", "mode", "amount", "currency",
            "date_begin", "date_end",
            "last_payed_date", "last_payed_status",
            "next_payment_date",
            "last_reason", "last_reason_code",
            "last_sync_at",
        )
        .first()
    )

    return JsonResponse(
        {"data": order, "subscription": sub},
        json_dumps_params={"ensure_ascii": False},
    )


def _get_strava_config():
    client_id = os.getenv("STRAVA_CLIENT_ID") or getattr(settings, "STRAVA_CLIENT_ID", None)
    client_secret = os.getenv("STRAVA_CLIENT_SECRET") or getattr(settings, "STRAVA_CLIENT_SECRET", None)
    deep_link = os.getenv("STRAVA_DEEP_LINK") or getattr(settings, "STRAVA_DEEP_LINK", None) or "velpas://oauth/strava"
    return client_id, client_secret, deep_link


def _exchange_strava_code(code: str):
    client_id, client_secret, _ = _get_strava_config()
    if not client_id or not client_secret:
        raise ValueError("STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET not configured")

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if response.status_code >= 400:
        raise ValueError(f"Strava token exchange failed: {response.text}")
    return response.json()


def _redirect_deep_link(target_url: str):
    response = HttpResponse(status=302)
    response["Location"] = target_url
    return response


def _refresh_strava_token(refresh_token: str):
    client_id, client_secret, _ = _get_strava_config()
    if not client_id or not client_secret:
        raise ValueError("STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET not configured")

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    if response.status_code >= 400:
        raise ValueError(f"Strava refresh failed: {response.text}")
    return response.json()


@require_GET
def strava_callback(request):
    error = request.GET.get("error")
    error_description = request.GET.get("error_description")
    code = request.GET.get("code")
    state = request.GET.get("state")

    _, _, deep_link = _get_strava_config()

    if error:
        params = {"error": error}
        if error_description:
            params["error_description"] = error_description
        if state:
            params["state"] = state
        return _redirect_deep_link(f"{deep_link}?{urlencode(params)}")

    if not code:
        return HttpResponseBadRequest("Missing code")

    try:
        token_data = _exchange_strava_code(code)
    except Exception:
        params = {"error": "token_exchange_failed"}
        if state:
            params["state"] = state
        return _redirect_deep_link(f"{deep_link}?{urlencode(params)}")

    params = {
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_at": str(token_data.get("expires_at", "")),
    }
    athlete = token_data.get("athlete") or {}
    if athlete.get("id") is not None:
        params["athlete_id"] = str(athlete.get("id"))
    if state:
        params["state"] = state

    return _redirect_deep_link(f"{deep_link}?{urlencode(params)}")


@csrf_exempt
@require_http_methods(["POST"])
def strava_exchange(request):
    code = request.POST.get("code")

    if not code and request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
            code = payload.get("code")
        except json.JSONDecodeError:
            code = None

    if not code:
        return JsonResponse({"detail": "Missing code"}, status=400)

    try:
        token_data = _exchange_strava_code(code)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except Exception:
        return JsonResponse({"detail": "Token exchange failed"}, status=400)

    return JsonResponse(token_data, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def strava_refresh(request):
    refresh_token = request.POST.get("refresh_token")

    if not refresh_token and request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
            refresh_token = payload.get("refresh_token")
        except json.JSONDecodeError:
            refresh_token = None

    if not refresh_token:
        return JsonResponse({"detail": "Missing refresh_token"}, status=400)

    try:
        token_data = _refresh_strava_token(refresh_token)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except Exception:
        return JsonResponse({"detail": "Token refresh failed"}, status=400)

    return JsonResponse(token_data, status=200)
