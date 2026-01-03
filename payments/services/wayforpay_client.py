import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass(frozen=True)
class WayForPayConfig:
    merchant_account: str
    merchant_password: str
    base_url: str = "https://api.wayforpay.com/regularApi"
    timeout_seconds: int = 25


class WayForPayRegularApiError(RuntimeError):
    pass


class WayForPayRegularClient:
    def __init__(self, config: WayForPayConfig):
        self.config = config

    def status(self, order_reference: str) -> Dict[str, Any]:
        payload = {
            "requestType": "STATUS",
            "merchantAccount": self.config.merchant_account,
            "merchantPassword": self.config.merchant_password,
            "orderReference": order_reference,
        }

        try:
            resp = requests.post(
                self.config.base_url,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as e:
            raise WayForPayRegularApiError(f"WayForPay request failed: {e}") from e

        try:
            data = resp.json()
        except ValueError as e:
            raise WayForPayRegularApiError(f"WayForPay returned non-JSON (HTTP {resp.status_code})") from e

        if resp.status_code >= 400:
            raise WayForPayRegularApiError(f"WayForPay HTTP {resp.status_code}: {data}")

        return data
