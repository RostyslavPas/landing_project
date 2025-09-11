import hashlib
import base64
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Order

def generate_signature(params: dict) -> str:
    signature_str = ";".join(str(params[k]) for k in [
        "merchantAccount",
        "merchantDomainName",
        "orderReference",
        "orderDate",
        "amount",
        "currency",
        "productName",
        "productCount",
        "productPrice"
    ])
    return base64.b64encode(
        hashlib.sha1((signature_str + settings.WAYFORPAY_SECRET).encode("utf-8")).digest()
    ).decode("utf-8")

def create_payment(request):
    order = Order.objects.create(
        product_name="Landing Product",
        amount=100.00,
        currency="UAH"
    )

    params = {
        "merchantAccount": settings.WAYFORPAY_ACCOUNT,
        "merchantDomainName": settings.WAYFORPAY_DOMAIN,
        "orderReference": str(order.id),
        "orderDate": int(order.created_at.timestamp()),
        "amount": str(order.amount),
        "currency": order.currency,
        "productName": [order.product_name],
        "productPrice": [str(order.amount)],
        "productCount": ["1"],
        "serviceUrl": f"https://{settings.WAYFORPAY_DOMAIN}/payments/callback/"
    }

    params["merchantSignature"] = generate_signature(params)
    return JsonResponse(params)

@csrf_exempt
def payment_callback(request):
    data = json.loads(request.body)
    order_id = data.get("orderReference")
    status = data.get("transactionStatus")

    try:
        order = Order.objects.get(id=order_id)
        order.status = status
        order.save()
    except Order.DoesNotExist:
        pass

    return JsonResponse({"status": "accept"})
