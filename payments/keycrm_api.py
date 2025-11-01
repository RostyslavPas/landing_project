import requests
import logging
from django.conf import settings

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
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
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

    def update_lead_payment_status(self, lead_id, payment_id, status="paid", description=None):
        """
        Оновити статус платежу через API картки воронки
        https://docs.keycrm.app/#/Pipelines/updateLeadPayment

        Args:
            lead_id: ID картки (ліда) в KeyCRM
            payment_id: ID платежу в KeyCRM
            status: Статус платежу (paid, not_paid, declined)
            description: Опис платежу
        """
        url = f"{self.base_url}/pipelines/cards/{lead_id}/payment/{payment_id}"
        try:
            payload = {"status": status}
            if description:
                payload["description"] = description

            logger.info(f"🔄 Оновлюємо платіж {payment_id} ліда {lead_id} на статус '{status}'")
            logger.info(f"📤 URL: {url}")
            logger.info(f"📤 Payload: {payload}")

            response = requests.put(url, headers=self.headers, json=payload, timeout=10)

            logger.info(f"📡 Статус відповіді: {response.status_code}")
            logger.info(f"📡 Відповідь: {response.text}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Платіж {payment_id} ліда {lead_id} оновлено на статус '{status}'")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при оновленні платежу {payment_id} ліда {lead_id}: {e}")
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
            logger.info(f"📤 URL: {url}")
            logger.info(f"📤 Payload: {payload}")

            response = requests.post(url, headers=self.headers, json=payload, timeout=10)

            logger.info(f"📡 Статус відповіді: {response.status_code}")
            logger.info(f"📡 Відповідь: {response.text}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Зовнішню транзакцію {transaction_id} прив'язано до платежу {payment_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при прив'язці зовнішньої транзакції: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None

    def attach_external_transaction_by_uuid(self, payment_id, transaction_uuid):
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

            logger.info(f"🔄 Прив'язуємо зовнішню транзакцію (UUID: {transaction_uuid}) до платежу {payment_id}")
            logger.info(f"📤 URL: {url}")
            logger.info(f"📤 Payload: {payload}")

            response = requests.post(url, headers=self.headers, json=payload, timeout=10)

            logger.info(f"📡 Статус відповіді: {response.status_code}")
            logger.info(f"📡 Відповідь: {response.text}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Зовнішню транзакцію (UUID: {transaction_uuid}) прив'язано до платежу {payment_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при прив'язці зовнішньої транзакції за UUID: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"🔻 Відповідь сервера: {e.response.text}")
            return None