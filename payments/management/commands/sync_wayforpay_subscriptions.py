from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from payments.models import Subscription, SubscriptionOrder
from payments.services.wayforpay_client import WayForPayRegularClient, WayForPayConfig


def _dt_from_unix(ts: Any) -> Optional[datetime]:
    """
    WayForPay здебільшого повертає unix timestamp (секунди).
    Але інколи можуть прилетіти строки (наприклад, "02.05.2034") — підтримаємо і це.
    """
    if ts in (None, "", 0):
        return None

    # unix timestamp (int/str)
    try:
        ts_int = int(ts)
        # WayForPay інколи повертає мілісекунди
        if ts_int > 10**11:
            ts_int = ts_int // 1000
        return datetime.fromtimestamp(ts_int, tz=dj_timezone.get_current_timezone())
    except Exception:
        pass

    # dd.mm.yyyy / dd-mm-yyyy / yyyy-mm-dd
    if isinstance(ts, str):
        s = ts.strip()
        for fmt in (
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M",
            "%d-%m-%Y",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                return dj_timezone.make_aware(dt, dj_timezone.get_current_timezone())
            except Exception:
                continue

    return None


def _normalize_status(wfp_status: Any) -> str:
    s = (str(wfp_status or "")).strip().lower()
    mapping = {
        "created": "created",
        "active": "active",
        "suspended": "suspended",
        "removed": "removed",
        "completed": "completed",
        # інколи можуть бути варіанти
        "confirm": "created",
        "confirmed": "created",
    }
    return mapping.get(s, "unknown")


def _pick_status_field(data: dict) -> str:
    # На практиці WayForPay повертає "status", але лишимо fallback
    return (
        data.get("status")
        or data.get("regularStatus")
        or data.get("regular_status")
        or ""
    )


def _has_meaningful_status_payload(data: dict) -> bool:
    """
    Якщо WayForPay повернув хоча б status/mode/nextPaymentDate/dateEnd — це вже корисний payload,
    навіть якщо reasonCode != 4100 (наприклад 4107 + status Removed).
    """
    return any(
        k in data and data.get(k) not in (None, "", 0)
        for k in (
            "status",
            "regularStatus",
            "regular_status",
            "mode",
            "regularMode",
            "regular_mode",
            "nextPaymentDate",
            "dateEnd",
            "dateBegin",
            "regularDateEnd",
            "regularDateBegin",
            "lastPayedDate",
            "lastPayedStatus",
        )
    )


def _safe_decimal_amount(v: Any):
    if v in (None, ""):
        return None
    try:
        # DecimalField у Django сам прийме str/Decimal; float небажано, але як fallback — ок
        return str(v)
    except Exception:
        return None


class Command(BaseCommand):
    help = "Sync subscriptions status from WayForPay regularApi (STATUS) into payments.Subscription"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional limit for number of unique orderReferences to sync (0 = no limit)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Include orders with any payment_status (by default only success)",
        )

    def handle(self, *args, **options):
        merchant_account = getattr(settings, "WAYFORPAY_MERCHANT_ACCOUNT", None)
        merchant_password = getattr(settings, "WAYFORPAY_MERCHANT_PASSWORD", None)

        if not merchant_account or not merchant_password:
            raise SystemExit(
                "WAYFORPAY_MERCHANT_ACCOUNT / WAYFORPAY_MERCHANT_PASSWORD are not set in settings/env"
            )

        client = WayForPayRegularClient(
            WayForPayConfig(
                merchant_account=merchant_account,
                merchant_password=merchant_password,
            )
        )

        qs = SubscriptionOrder.objects.exclude(
            wayforpay_order_reference__isnull=True
        ).exclude(
            wayforpay_order_reference__exact=""
        )

        if not options.get("all"):
            qs = qs.filter(payment_status="success")

        qs = qs.order_by("-created_at")

        limit = int(options.get("limit") or 0)

        total = 0
        updated = 0
        skipped = 0
        failed = 0

        seen_refs: set[str] = set()

        for order in qs:
            order_ref = (order.wayforpay_order_reference or "").strip()
            if not order_ref:
                skipped += 1
                continue

            # ✅ дедуп по orderReference
            if order_ref in seen_refs:
                skipped += 1
                continue
            seen_refs.add(order_ref)

            total += 1
            if limit > 0 and total > limit:
                break

            try:
                data = client.status(order_ref)
            except Exception as e:
                failed += 1
                self.stderr.write(f"[FAIL] {order_ref}: {e}")
                continue

            reason_code = data.get("reasonCode")
            reason = (data.get("reason") or data.get("message") or "").strip()

            # ✅ створюємо/дістаємо Subscription завжди (щоб "усі підписки відображались")
            sub, _ = Subscription.objects.get_or_create(
                order_reference=order_ref,
                defaults={
                    "source_order": order,
                    "name": order.name or "",
                    "email": order.email or "",
                    "phone": order.phone or "",
                    "currency": "",
                    "status": "unknown",
                },
            )

            # ✅ завжди оновимо контакти/посилання на source_order
            if not sub.source_order:
                sub.source_order = order
            sub.name = order.name or sub.name
            sub.email = order.email or sub.email
            sub.phone = order.phone or sub.phone

            # ✅ якщо payload містить статусні поля — оновлюємо їх навіть при reasonCode != 4100
            if _has_meaningful_status_payload(data):
                wfp_status = _pick_status_field(data)
                sub.status = _normalize_status(wfp_status)

                sub.mode = (data.get("mode") or data.get("regularMode") or sub.mode or "").strip()
                sub.currency = (data.get("currency") or data.get("regularCurrency") or sub.currency or "").strip()

                amt = data.get("regularAmount") if data.get("regularAmount") is not None else data.get("amount")
                amt_norm = _safe_decimal_amount(amt)
                if amt_norm is not None:
                    try:
                        sub.amount = amt_norm
                    except Exception:
                        pass

                sub.date_begin = _dt_from_unix(data.get("dateBegin") or data.get("regularDateBegin"))
                sub.date_end = _dt_from_unix(data.get("dateEnd") or data.get("regularDateEnd"))

                # nextPaymentDate інколи є навіть для Removed — це може плутати в UI.
                next_dt = _dt_from_unix(data.get("nextPaymentDate"))
                if sub.status in ("removed", "completed"):
                    sub.next_payment_date = None
                else:
                    sub.next_payment_date = next_dt

            else:
                # payload не містить корисних статусних полів — лишимо unknown
                sub.status = sub.status or "unknown"

            # ✅ оновлюємо lastPayed* навіть якщо немає інших полів
            if data.get("lastPayedDate") not in (None, "", 0):
                sub.last_payed_date = _dt_from_unix(data.get("lastPayedDate"))
            if data.get("lastPayedStatus") not in (None, ""):
                sub.last_payed_status = (data.get("lastPayedStatus") or "").strip()

            # ✅ завжди зберігаємо reason/reasonCode/raw + sync time
            sub.last_reason_code = reason_code
            sub.last_reason = reason
            sub.last_sync_raw = data
            sub.last_sync_at = dj_timezone.now()

            # ✅ збережемо все одним save
            sub.save(update_fields=[
                "source_order", "name", "email", "phone",
                "status", "mode", "amount", "currency",
                "date_begin", "date_end", "last_payed_date", "last_payed_status", "next_payment_date",
                "last_reason", "last_reason_code", "last_sync_at", "last_sync_raw",
                "updated_at",
            ])

            updated += 1
            self.stdout.write(
                f"[OK] {order_ref}: status={sub.status} reasonCode={reason_code} next={sub.next_payment_date}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Done. total={total} updated={updated} failed={failed} skipped={skipped}"
        ))
