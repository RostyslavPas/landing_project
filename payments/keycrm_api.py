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

    def get_payments(self, lead_id):
        """Отримати платежі для ліда"""
        url = f"{self.base_url}/pipelines/cards/{lead_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            card_data = response.json().get("data", {})
            return card_data.get("payments", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при отриманні платежів: {e}")
            return []

    def create_payment(self, card_id, data):
        """Створити платіж для картки (ліда)"""
        url = f"{self.base_url}/pipelines/cards/{card_id}/payment"
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж створено для картки {card_id}: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при створенні платежу для картки {card_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def update_payment_status(self, payment_id, status="paid", description=None):
        """Оновити статус та опис платежу"""
        url = f"{self.base_url}/payments/{payment_id}"
        try:
            payload = {"status": status}
            if description:
                payload["description"] = description
            
            response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж {payment_id} оновлено: статус={status}, опис={description}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при оновленні платежу {payment_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def add_external_transaction(self, payment_id, transaction_data):
        """Додати зовнішню транзакцію до оплати"""
        url = f"{self.base_url}/payments/{payment_id}/external-transactions"
        try:
            response = requests.post(url, headers=self.headers, json=transaction_data, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Зовнішня транзакція додана до платежу {payment_id}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при додаванні зовнішньої транзакції: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def create_payment_for_card(self, card_id, payment_data):
        """Створити платіж для картки після створення ліда"""
        url = f"{self.base_url}/pipelines/cards/{card_id}/payments"
        try:
            response = requests.post(url, json=payment_data, headers=self.headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж створено для картки {card_id}: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при створенні платежу: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def update_lead_payment_status(self, lead_id, payment_id, status="paid", description=None):
        """Оновити статус платежу через API ліда"""
        url = f"{self.base_url}/pipelines/cards/{lead_id}/payments/{payment_id}"
        try:
            payload = {"status": status}
            if description:
                payload["description"] = description
            
            response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж {payment_id} ліда {lead_id} оновлено: статус={status}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при оновленні платежу {payment_id} ліда {lead_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def update_payment_status_direct(self, payment_id, status="paid", description=None):
        """Прямий PATCH запит для оновлення статусу платежу"""
        url = f"{self.base_url}/payments/{payment_id}"
        try:
            payload = {"status": status}
            if description:
                payload["description"] = description
        
            logger.info(f"🔄 Прямий PATCH запит до {url} з даними: {payload}")
            response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
            
            logger.info(f"📡 Статус відповіді: {response.status_code}")
            logger.info(f"📡 Відповідь: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж {payment_id} оновлено: статус={status}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при прямому оновленні платежу {payment_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def update_lead_status(self, lead_id, status_id):
        """Оновити статус ліда в воронці"""
        url = f"{self.base_url}/pipelines/cards/{lead_id}"
        try:
            payload = {"status_id": status_id}
            
            logger.info(f"🔄 Оновлюємо статус ліда {lead_id} на {status_id}")
            response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Статус ліда {lead_id} оновлено на {status_id}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при оновленні статусу ліда {lead_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None
