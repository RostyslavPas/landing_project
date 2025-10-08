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

    def add_external_transaction(self, payment_id, data):
        """Додати зовнішню транзакцію до оплати"""
        url = f"{self.base_url}/payments/{payment_id}/external-transactions"
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при додаванні зовнішньої транзакції: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
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
