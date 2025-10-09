import requests
import logging
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)


class KeyCRMAPI:
    """Клас для інтеграції з KeyCRM API"""

    def __init__(self):
        self.api_token = settings.KEYCRM_API_TOKEN
        self.base_url = "https://openapi.keycrm.app/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def create_pipeline_card(self, data):
        """Створення картки (лід) у воронці KeyCRM."""
        url = f"{self.base_url}/pipelines/cards"
        try:
            logger.info(f"➡️ Надсилаю запит на створення картки в KeyCRM: {data}")
            response = requests.post(url, json=data, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            card_id = result.get("id") or result.get("data", {}).get("id")
            logger.info(f"✅ Лід створено успішно (ID: {card_id}) | Відповідь: {result}")

            return {"id": card_id, "response": result}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при створенні картки в KeyCRM: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def get_pipelines(self):
        """Отримати список воронок"""
        url = f"{self.base_url}/pipelines"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при отриманні воронок: {e}")
            return None

    def get_sources(self):
        """Отримати список джерел"""
        url = f"{self.base_url}/sources"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при отриманні джерел: {e}")
            return None

    # def get_payments(self, lead_id):
    #     """Отримати платежі для ліда"""
    #     url = f"{self.base_url}/pipelines/cards/{lead_id}"
    #     try:
    #         response = requests.get(url, headers=self.headers, timeout=10)
    #         response.raise_for_status()
    #         card_data = response.json().get("data", {})
    #         return card_data.get("payments", [])
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при отриманні платежів: {e}")
    #         return []
    #
    # def create_payment(self, card_id, data):
    #     """Створити платіж для картки (ліда)"""
    #     url = f"{self.base_url}/pipelines/cards/{card_id}/payment"
    #     try:
    #         response = requests.post(url, json=data, headers=self.headers, timeout=10)
    #         response.raise_for_status()
    #         result = response.json()
    #         logger.info(f"✅ Платіж створено для картки {card_id}: {result}")
    #         return result
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при створенні платежу для картки {card_id}: {e}")
    #         if hasattr(e, "response") and e.response is not None:
    #             logger.error(f"🔻 Відповідь сервера: {e.response.text}")
    #         return None

    def update_payment_status(self, payment_id, status="paid", description=None):
        """
        Оновити статус платежу (PUT запит згідно з документацією KeyCRM)
        https://docs.keycrm.app/#/Payments/updatePayment
        """
        url = f"{self.base_url}/payments/{payment_id}"
        try:
            payload = {"status": status}
            if description:
                payload["description"] = description

            logger.info(f"🔄 Оновлюємо статус платежу {payment_id} на '{status}'")
            logger.info(f"📤 Payload: {payload}")

            response = requests.put(url, headers=self.headers, json=payload, timeout=10)

            logger.info(f"📡 Статус відповіді: {response.status_code}")
            logger.info(f"📡 Відповідь: {response.text}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж {payment_id} оновлено на статус '{status}'")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при оновленні платежу {payment_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def attach_external_transaction(self, payment_id, transaction_uuid):
        """
        Прив'язати зовнішню транзакцію до платежу за UUID
        https://docs.keycrm.app/#/Payments/attachExternalTransactionToPayment

        Args:
            payment_id: ID платежу в KeyCRM
            transaction_uuid: Унікальний ідентифікатор транзакції від платіжного сервісу
        """
        url = f"{self.base_url}/payments/{payment_id}/external-transactions"
        try:
            payload = {"transaction_uuid": transaction_uuid}

            logger.info(f"🔄 Прив'язуємо зовнішню транзакцію до платежу {payment_id}")
            logger.info(f"📤 Transaction UUID: {transaction_uuid}")

            response = requests.post(url, headers=self.headers, json=payload, timeout=10)

            logger.info(f"📡 Статус відповіді: {response.status_code}")
            logger.info(f"📡 Відповідь: {response.text}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Зовнішню транзакцію прив'язано до платежу {payment_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при прив'язці зовнішньої транзакції: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def get_external_transactions(self, description=None, limit=50, offset=0):
        """
        Отримати список зовнішніх транзакцій
        https://docs.keycrm.app/#/Payments/getPaginatedListOfExternalTransactions

        Args:
            description: Фільтр по опису (номер замовлення, ПІБ тощо)
            limit: Кількість записів
            offset: Зсув для пагінації
        """
        url = f"{self.base_url}/payments/external-transactions"
        try:
            params = {"limit": limit, "offset": offset}
            if description:
                params["description"] = description

            logger.info(f"🔄 Отримуємо список зовнішніх транзакцій")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Отримано {len(result.get('data', []))} транзакцій")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при отриманні зовнішніх транзакцій: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    # def create_payment_for_card(self, card_id, payment_data):
    #     """Створити платіж для картки після створення ліда"""
    #     url = f"{self.base_url}/pipelines/cards/{card_id}/payments"
    #     try:
    #         response = requests.post(url, json=payment_data, headers=self.headers, timeout=10)
    #         response.raise_for_status()
    #         result = response.json()
    #         logger.info(f"✅ Платіж створено для картки {card_id}: {result}")
    #         return result
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при створенні платежу: {e}")
    #         if hasattr(e, "response") and e.response is not None:
    #             logger.error(f"🔻 Відповідь сервера: {e.response.text}")
    #         return None
    #
    # def update_lead_payment_status(self, lead_id, payment_id, status="paid", description=None):
    #     """Оновити статус платежу через API ліда"""
    #     url = f"{self.base_url}/pipelines/cards/{lead_id}/payments/{payment_id}"
    #     try:
    #         payload = {"status": status}
    #         if description:
    #             payload["description"] = description
    #
    #         response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
    #         response.raise_for_status()
    #         result = response.json()
    #         logger.info(f"✅ Платіж {payment_id} ліда {lead_id} оновлено: статус={status}")
    #         return result
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при оновленні платежу {payment_id} ліда {lead_id}: {e}")
    #         if hasattr(e, "response") and e.response is not None:
    #             logger.error(f"🔻 Відповідь сервера: {e.response.text}")
    #         return None
    #
    # def update_payment_status_direct(self, payment_id, status="paid", description=None):
    #     """Прямий PATCH запит для оновлення статусу платежу"""
    #     url = f"{self.base_url}/payments/{payment_id}"
    #     try:
    #         payload = {"status": status}
    #         if description:
    #             payload["description"] = description
    #
    #         logger.info(f"🔄 Прямий PUT запит до {url} з даними: {payload}")
    #         response = requests.put(url, headers=self.headers, json=payload, timeout=10)
    #
    #         logger.info(f"📡 Статус відповіді: {response.status_code}")
    #         logger.info(f"📡 Відповідь: {response.text}")
    #
    #         response.raise_for_status()
    #         result = response.json()
    #         logger.info(f"✅ Платіж {payment_id} оновлено: статус={status}")
    #         return result
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при прямому оновленні платежу {payment_id}: {e}")
    #         if hasattr(e, "response") and e.response is not None:
    #             logger.error(f"🔻 Відповідь сервера: {e.response.text}")
    #         return None

    def attach_external_transaction_by_id(self, payment_id, transaction_id):
        """
        Прив'язати зовнішню транзакцію до платежу за ID транзакції
        https://docs.keycrm.app/#/Payments/attachExternalTransactionToPayment

        Args:
            payment_id: ID платежу в KeyCRM
            transaction_id: ID транзакції з списку зовнішніх транзакцій
        """
        url = f"{self.base_url}/payments/{payment_id}/external-transactions"
        try:
            payload = {"transaction_id": transaction_id}

            logger.info(f"🔄 Прив'язуємо зовнішню транзакцію (ID: {transaction_id}) до платежу {payment_id}")

            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Зовнішню транзакцію {transaction_id} прив'язано до платежу {payment_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при прив'язці зовнішньої транзакції: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    # def update_lead_status(self, lead_id, status_id, client_id=None):
    #     """Оновити статус ліда в воронці"""
    #     url = f"{self.base_url}/pipelines/cards/{lead_id}"
    #     try:
    #         payload = {"status_id": status_id}
    #         if client_id:
    #             payload["client_id"] = client_id
    #
    #         logger.info(f"🔄 Оновлюємо статус ліда {lead_id} на {status_id} з client_id: {client_id}")
    #         response = requests.put(url, headers=self.headers, json=payload, timeout=10)
    #         response.raise_for_status()
    #         result = response.json()
    #         logger.info(f"✅ Статус ліда {lead_id} оновлено на {status_id}")
    #         return result
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при оновленні статусу ліда {lead_id}: {e}")
    #         if hasattr(e, "response") and e.response is not None:
    #             logger.error(f"🔻 Відповідь сервера: {e.response.text}")
    #         return None

    # def update_payment_with_transaction(self, payment_id, order, wayforpay_data):
    #     """Оновити платіж з зовнішньою транзакцією (повний PUT запит)"""
    #     url = f"https://pasue.api.keycrm.app/finance/payments/{payment_id}"
    #     try:
    #         payload = {
    #             'destination_type': 'lead',
    #             'destination_id': order.keycrm_lead_id,
    #             'payment_id': payment_id,
    #             'payment_method_id': 6,  # WayForPay
    #             'status': 'paid',
    #             'actual_amount': float(order.amount),
    #             'description': f"Замовлення #{order.wayforpay_order_reference}. Клієнт: {order.name}, {order.phone}, {order.email}. Товари: PASUE Club - Grand Opening Party Ticket",
    #             'transaction_uuid': order.wayforpay_order_reference,
    #             'gateway_transaction_id': wayforpay_data.get('authCode'),
    #             'gateway_id': 1,
    #             'currency_code': 'UAH',
    #             'payment_date': datetime.now().isoformat() + 'Z',
    #         }
    #
    #         logger.info(f"🔄 Оновлюємо платіж {payment_id} з транзакцією: {payload}")
    #         response = requests.put(url, headers=self.headers, json=payload, timeout=10)
    #         response.raise_for_status()
    #         result = response.json()
    #         logger.info(f"✅ Платіж {payment_id} оновлено з транзакцією")
    #         return result
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"❌ Помилка при оновленні платежу {payment_id}: {e}")
    #         if hasattr(e, "response") and e.response is not None:
    #             logger.error(f"🔻 Відповідь сервера: {e.response.text}")
    #         return None
