from __future__ import annotations

from typing import Any, Dict, Optional

from django.core.management.base import BaseCommand

from payments.models import Subscription


EMAIL_KEYS = ("clientEmail", "email", "client_email")
PHONE_KEYS = ("clientPhone", "phone", "client_phone")
NAME_KEYS = ("clientName", "clientFirstName")


def _pick_value(raw: Dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw.get(key)
        if value:
            return str(value).strip()
    return ""


class Command(BaseCommand):
    help = "Backfill SubscriptionOrder.wfp_* fields from Subscription.last_sync_raw"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Persist changes (default: dry-run)")

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        updated = 0
        scanned = 0

        qs = Subscription.objects.select_related("source_order").all()
        for sub in qs:
            scanned += 1
            if not sub.source_order:
                continue
            raw: Optional[Dict[str, Any]] = sub.last_sync_raw or None
            if not isinstance(raw, dict):
                continue

            email = _pick_value(raw, EMAIL_KEYS).lower()
            phone = _pick_value(raw, PHONE_KEYS)
            name = _pick_value(raw, NAME_KEYS)

            if not (email or phone or name):
                continue

            order = sub.source_order
            before = (order.wfp_email, order.wfp_phone, order.wfp_name)

            if email and not order.wfp_email:
                order.wfp_email = email
            if phone and not order.wfp_phone:
                order.wfp_phone = phone
            if name and not order.wfp_name:
                order.wfp_name = name

            after = (order.wfp_email, order.wfp_phone, order.wfp_name)
            if before == after:
                continue

            if apply_changes:
                order.save(update_fields=["wfp_email", "wfp_phone", "wfp_name"])
            updated += 1
            self.stdout.write(
                f"{'updated' if apply_changes else 'dry-run'}: "
                f"subscription#{sub.id} -> order#{order.id} "
                f"email={order.wfp_email or '-'} phone={order.wfp_phone or '-'} name={order.wfp_name or '-'}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. scanned={scanned} updated={updated} apply={apply_changes}"
            )
        )
