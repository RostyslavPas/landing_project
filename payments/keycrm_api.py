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

    # ==========================================================
    # 1️⃣ СТВОРЕННЯ КАРТКИ (лід у воронці)
    # ==========================================================
    def create_pipeline_card(self, data):
        """
        Створення картки (лід) у воронці KeyCRM.
        Docs: https://docs.keycrm.app/#/Pipelines/createNewPipelineCard
        """
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

    # ==========================================================
    # 2️⃣ ДОДАВАННЯ ЗОВНІШНЬОЇ ТРАНЗАКЦІЇ (оплати)
    # ==========================================================
    def create_external_transaction(self, data):
        """
        Додавання зовнішньої транзакції (оплати)
        Docs: https://help.keycrm.app/uk/process-automation-api-and-more/iak-pratsiuvati-z-oplatami-v-api
        """
        url = f"{self.base_url}/external/transactions"

        payload = {
            "external_id": data["external_id"],             # унікальний ID (наприклад WayForPay transactionId)
            "amount": data["amount"],                       # сума оплати
            "status": data.get("status", "paid"),           # paid | declined | refund
            "payment_system": data.get("payment_system", "WayForPay"),
            "buyer_phone": data.get("buyer_phone"),
            "buyer_email": data.get("buyer_email"),
            "description": data.get("comment", ""),
            "date_paid": data.get("date_paid", datetime.utcnow().isoformat()),
            "card_title": data.get("card_title", "Онлайн оплата"),
        }

        try:
            logger.info(f"➡️ Надсилаю зовнішню транзакцію до KeyCRM: {payload}")
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Зовнішню транзакцію створено: {result}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при створенні зовнішньої транзакції: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    # ==========================================================
    # 3️⃣ ДОДАТКОВІ СЕРВІСНІ МЕТОДИ
    # ==========================================================
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