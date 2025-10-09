from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import hmac
import time
import hashlib
import json
from .keycrm_api import KeyCRMAPI
from .forms import TicketOrderForm
import logging
from django.shortcuts import render
from .models import TicketOrder
from .ticket_utils import send_ticket_email_with_pdf


logger = logging.getLogger(__name__)


def is_staff(user):
    return user.is_staff


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

            # Створюємо замовлення
            order = TicketOrder.objects.create(
                name=name,
                email=email,
                phone=phone,
                payment_status="pending",
                amount=1.00,
                device_type=device_type,
            )

            logger.info(f"📝 Створено замовлення #{order.id}")

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

            # Генеруємо параметри для оплати
            params = generate_wayforpay_params(order)
            return JsonResponse({"success": True, "wayforpay_params": params})

        else:
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)

    return JsonResponse({"success": False}, status=405)


# @csrf_exempt
# @require_http_methods(["POST"])
# def wayforpay_callback(request):
#     """Webhook від WayForPay"""
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#         logger.info("=== CALLBACK DATA ===")
#         logger.info(json.dumps(data, indent=2, ensure_ascii=False))
#         logger.info("=== END CALLBACK DATA ===")
#
#         order_reference = data.get("orderReference")
#         transaction_status = data.get("transactionStatus")
#         merchant_signature = data.get("merchantSignature")
#
#         if not order_reference:
#             return HttpResponse("Missing orderReference", status=400)
#
#         try:
#             order = TicketOrder.objects.get(wayforpay_order_reference=order_reference)
#             logger.info(f"Знайдено замовлення #{order.id}, KeyCRM lead id: {order.keycrm_lead_id}")
#         except TicketOrder.DoesNotExist:
#             logger.info(f"Order not found: {order_reference}")
#             return HttpResponse("Order not found", status=404)
#
#         # Перевірка на повторний callback
#         if order.callback_processed and order.payment_status == "success":
#             logger.info(f"ℹ️ Callback вже оброблено для замовлення #{order.id}")
#             status = "accept"
#             ts = int(time.time())
#             sig_source = f"{order_reference};{status};{settings.WAYFORPAY_SECRET_KEY}"
#             response_signature = hmac.new(
#                 settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
#                 sig_source.encode("utf-8"),
#                 hashlib.md5
#             ).hexdigest()
#             return JsonResponse({
#                 "orderReference": order_reference,
#                 "status": status,
#                 "time": ts,
#                 "signature": response_signature
#             })
#
#         # Формуємо підпис для перевірки
#         signature_fields = [
#             data.get("merchantAccount", ""),
#             data.get("orderReference", ""),
#             str(data.get("amount", "")),
#             data.get("currency", ""),
#             str(data.get("authCode", "")),
#             data.get("cardPan", ""),
#             str(data.get("transactionStatus", "")),
#             str(data.get("reasonCode", "")),
#         ]
#         signature_string = ";".join(signature_fields)
#         expected_signature = hmac.new(
#             settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
#             signature_string.encode("utf-8"),
#             hashlib.md5
#         ).hexdigest()
#
#         logger.info("=== CALLBACK SIGNATURE DEBUG ===")
#         logger.info(f"Expected signature: {expected_signature}")
#         logger.info(f"Received signature: {merchant_signature}")
#
#         if expected_signature != merchant_signature:
#             logger.error("=== SIGNATURE MISMATCH ===")
#             return HttpResponse("Invalid signature", status=403)
#
#         logger.info("=== SIGNATURE VALID ===")
#
#         # Оновлюємо статус замовлення
#         if transaction_status == "Approved":
#             order.payment_status = "success"
#             order.callback_processed = True
#             order.name = data.get("clientFirstName", order.name)
#             order.email = data.get("clientEmail", order.email)
#             order.phone = data.get("clientPhone", order.phone)
#             order.save()
#
#             logger.info(f"✅ Замовлення #{order.id} позначено як оплачене")
#
#             # Відправка email
#             if order.email_status != "sent":
#                 try:
#                     send_ticket_email_with_pdf(order)
#                     order.email_status = "sent"
#                     order.save(update_fields=["email_status"])
#                     logger.info(f"📧 Email відправлено для замовлення #{order.id}")
#                 except Exception as e:
#                     logger.error(f"❌ Помилка відправки email для замовлення #{order.id}: {e}")
#             else:
#                 logger.info(f"ℹ️ Email вже було відправлено для замовлення #{order.id}")
#
#             # === KeyCRM оновлення ===
#             if order.keycrm_payment_id and settings.KEYCRM_API_TOKEN:
#                 try:
#                     keycrm = KeyCRMAPI()
#
#                     # 1️⃣ Спочатку оновлюємо статус платежу на "paid"
#                     payment_description = f"Замовлення #{order.wayforpay_order_reference}. Клієнт: {order.name}, {order.phone}, {order.email}"
#
#                     logger.info(f"🔄 Оновлюємо статус платежу {order.keycrm_payment_id} на 'paid'")
#                     payment_update_result = keycrm.update_payment_status(
#                         payment_id=order.keycrm_payment_id,
#                         status="paid",
#                         description=payment_description
#                     )
#
#                     if payment_update_result:
#                         logger.info(f"✅ Статус платежу {order.keycrm_payment_id} оновлено на 'paid'")
#
#                         # 2️⃣ Прив'язуємо зовнішню транзакцію за UUID
#                         logger.info(f"🔄 Прив'язуємо зовнішню транзакцію {order.wayforpay_order_reference}")
#                         transaction_result = keycrm.attach_external_transaction(
#                             payment_id=order.keycrm_payment_id,
#                             transaction_uuid=order.wayforpay_order_reference
#                         )
#
#                         if transaction_result:
#                             logger.info(f"✅ Зовнішня транзакція прив'язана до платежу {order.keycrm_payment_id}")
#                         else:
#                             # Якщо прив'язка по UUID не спрацювала, можна спробувати знайти транзакцію в списку
#                             logger.warning(f"⚠️ Не вдалося прив'язати транзакцію за UUID")
#                             logger.info(f"🔄 Спроба знайти транзакцію в списку зовнішніх транзакцій")
#
#                             # Шукаємо транзакцію по orderReference у description
#                             transactions = keycrm.get_external_transactions(
#                                 description=order.wayforpay_order_reference
#                             )
#
#                             if transactions and transactions.get('data'):
#                                 transaction_list = transactions['data']
#                                 if len(transaction_list) > 0:
#                                     transaction_id = transaction_list[0].get('id')
#                                     logger.info(f"🔍 Знайдено транзакцію ID: {transaction_id}")
#
#                                     # Прив'язуємо за ID
#                                     attach_result = keycrm.attach_external_transaction_by_id(
#                                         payment_id=order.keycrm_payment_id,
#                                         transaction_id=transaction_id
#                                     )
#
#                                     if attach_result:
#                                         logger.info(f"✅ Транзакцію {transaction_id} прив'язано до платежу")
#                                     else:
#                                         logger.warning(f"⚠️ Не вдалося прив'язати транзакцію за ID")
#                                 else:
#                                     logger.warning(f"⚠️ Транзакцію не знайдено в списку")
#                             else:
#                                 logger.warning(f"⚠️ Не вдалося отримати список транзакцій")
#                     else:
#                         logger.warning(f"⚠️ Не вдалося оновити статус платежу {order.keycrm_payment_id}")
#
#                 except Exception as e:
#                     logger.error(f"❌ Помилка при роботі з KeyCRM: {e}")
#                     import traceback
#                     logger.error(f"Traceback: {traceback.format_exc()}")
#             else:
#                 if not order.keycrm_payment_id:
#                     logger.warning(f"⚠️ KeyCRM payment_id відсутній для замовлення #{order.id}")
#                 if not settings.KEYCRM_API_TOKEN:
#                     logger.warning(f"⚠️ KEYCRM_API_TOKEN не налаштований")
#
#         elif transaction_status == "Declined":
#             order.payment_status = "failed"
#             order.callback_processed = True
#             order.save()
#             logger.info(f"❌ Оплата відхилена для замовлення #{order.id}")
#
#             # Опціонально: можна оновити статус платежу в KeyCRM на "declined"
#             if order.keycrm_payment_id and settings.KEYCRM_API_TOKEN:
#                 try:
#                     keycrm = KeyCRMAPI()
#                     keycrm.update_payment_status(
#                         payment_id=order.keycrm_payment_id,
#                         status="declined",
#                         description=f"Оплата відхилена. Причина: {data.get('reasonCode', 'Unknown')}"
#                     )
#                 except Exception as e:
#                     logger.error(f"❌ Помилка при оновленні статусу відхиленого платежу: {e}")
#
#         else:
#             order.payment_status = "failed"
#             order.callback_processed = True
#             order.save()
#             logger.info(f"⚠️ Невідомий статус транзакції: {transaction_status}")
#
#         # Підтвердження для WayForPay
#         status = "accept"
#         ts = int(time.time())
#         sig_source = f"{order_reference};{status};{settings.WAYFORPAY_SECRET_KEY}"
#
#         response_signature = hmac.new(
#             settings.WAYFORPAY_SECRET_KEY.encode("utf-8"),
#             sig_source.encode("utf-8"),
#             hashlib.md5
#         ).hexdigest()
#
#         response_data = {
#             "orderReference": order_reference,
#             "status": status,
#             "time": ts,
#             "signature": response_signature,
#         }
#
#         return JsonResponse(response_data, status=200)
#
#     except Exception as e:
#         logger.error(f"❌ Callback error: {str(e)}")
#         import traceback
#         logger.error(f"Traceback: {traceback.format_exc()}")
#         return HttpResponse(f"Error: {str(e)}", status=400)
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
                                    # 1. Сума співпадає
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

