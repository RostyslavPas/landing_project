import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class KeyCRMAPI:
    """Клас для роботи з API KeyCRM"""

    def __init__(self):
        self.api_token = settings.KEYCRM_API_TOKEN
        self.base_url = "https://openapi.keycrm.app/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def create_lead(self, data):
        """
        Створення ліда у KeyCRM

        Args:
            data (dict): Дані ліда
                - buyer_name (str): Ім'я клієнта (опціонально)
                - buyer_phone (str): Телефон клієнта
                - buyer_email (str): Email клієнта
                - source_id (int): ID джерела
                - pipeline_id (int): ID воронки
                - price (float): Сума замовлення
                - comment (str): Коментар (опціонально)

        Returns:
            dict: Відповідь від API або None у випадку помилки
        """
        url = f"{self.base_url}/leads"

        try:
            logger.info(f"Створення ліда в KeyCRM з даними: {data}")
            response = requests.post(url, json=data, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Відповідь від KeyCRM: {result}")

            # KeyCRM може повертати різну структуру
            lead_id = None
            if isinstance(result, dict):
                # Перевіряємо різні варіанти структури відповіді
                lead_id = result.get('id') or result.get('data', {}).get('id')

            if lead_id:
                logger.info(f"Лід успішно створено в KeyCRM. ID: {lead_id}")
                return {'id': lead_id, 'full_response': result}
            else:
                logger.warning(f"ID ліда не знайдено у відповіді: {result}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при створенні ліда в KeyCRM: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Статус код: {e.response.status_code}")
                logger.error(f"Відповідь сервера: {e.response.text}")
            return None

    def update_lead(self, lead_id, data):
        """
        Оновлення ліда (додавання коментаря)

        Args:
            lead_id (int): ID ліда
            data (dict): Дані для оновлення (comment)

        Returns:
            dict: Відповідь від API або None
        """
        # Використовуємо endpoint для додавання коментаря до ліда
        url = f"{self.base_url}/leads/{lead_id}/notes"

        # Формуємо дані для коментаря
        note_data = {
            "text": data.get("comment", "")
        }

        try:
            logger.info(f"Додавання коментаря до ліда {lead_id}: {note_data}")
            response = requests.post(url, json=note_data, headers=self.headers, timeout=10)

            # Якщо endpoint для notes не працює, пробуємо прямий update
            if response.status_code == 404:
                logger.warning(f"Endpoint /notes не працює, пробуємо PUT /leads/{lead_id}")
                url = f"{self.base_url}/leads/{lead_id}"
                response = requests.put(url, json=data, headers=self.headers, timeout=10)

            response.raise_for_status()

            result = response.json()
            logger.info(f"Лід {lead_id} успішно оновлено. Відповідь: {result}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при оновленні ліда {lead_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Статус код: {e.response.status_code}")
                logger.error(f"Відповідь сервера: {e.response.text}")

            # Не критична помилка - лід вже створено
            logger.info("Продовжуємо роботу, оновлення ліда не критичне")
            return None

    def update_payment_status(self, lead_id, payment_data):
        """
        Оновлення статусу оплати для ліда

        Args:
            lead_id (int): ID ліда в KeyCRM
            payment_data (dict): Дані про оплату
                - payment_id (int/str): ID оплати в KeyCRM (якщо відомий)
                - status (str): Статус оплати: "paid", "not_paid", "refund", "declined"
                - amount (float): Сума оплати
                - payment_method (str): Спосіб оплати (опціонально)
                - comment (str): Коментар (опціонально)

        Returns:
            dict: Відповідь від API або None
        """
        try:
            # Спочатку отримуємо лід щоб знайти ID оплати
            lead_data = self.get_lead(lead_id)

            if not lead_data:
                logger.error(f"Не вдалося отримати дані ліда {lead_id}")
                return None

            # Шукаємо ID оплати в ліді
            payment_id = None
            payments = lead_data.get('payments', [])

            if payments and len(payments) > 0:
                # Беремо першу оплату (або можна шукати по сумі)
                payment_id = payments[0].get('id')

            if not payment_id:
                logger.warning(f"ID оплати не знайдено для ліда {lead_id}")
                # Якщо оплати немає, створюємо нову

            # Оновлюємо існуючу оплату
            url = f"{self.base_url}/payments/{payment_id}"

            update_data = {
                "status": payment_data.get("status", "paid"),
                "amount": payment_data.get("amount"),
            }

            if payment_data.get("payment_method"):
                update_data["payment_method"] = payment_data["payment_method"]

            if payment_data.get("comment"):
                update_data["description"] = payment_data["comment"]

            logger.info(f"Оновлення оплати {payment_id} для ліда {lead_id}: {update_data}")
            response = requests.put(url, json=update_data, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Оплата успішно оновлена. Відповідь: {result}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при оновленні оплати для ліда {lead_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Статус код: {e.response.status_code}")
                logger.error(f"Відповідь сервера: {e.response.text}")
            return None

    def get_pipelines(self):
        """
        Отримання списку воронок

        Returns:
            list: Список воронок або None
        """
        url = f"{self.base_url}/pipelines"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Отримано воронок: {len(result) if isinstance(result, list) else 'unknown'}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при отриманні воронок: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Відповідь сервера: {e.response.text}")
            return None

    def get_sources(self):
        """
        Отримання списку джерел

        Returns:
            list: Список джерел або None
        """
        url = f"{self.base_url}/sources"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Отримано джерел: {len(result) if isinstance(result, list) else 'unknown'}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при отриманні джерел: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Відповідь сервера: {e.response.text}")
            return None

    def get_lead(self, lead_id):
        """
        Отримання інформації про лід

        Args:
            lead_id (int): ID ліда

        Returns:
            dict: Дані ліда або None
        """
        url = f"{self.base_url}/leads/{lead_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Отримано інформацію про лід {lead_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при отриманні ліда {lead_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Статус код: {e.response.status_code}")
                logger.error(f"Відповідь сервера: {e.response.text}")
            return None