from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import calendar
from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.models import Subscription


INACTIVE_STATUSES = {"removed", "suspended", "completed"}
PAID_STATUSES = {"approved", "paid", "success"}


@dataclass
class RemovalCandidate:
    subscription_id: int
    email: str
    phone: str
    status: str
    last_payed_status: str
    next_payment_date: datetime | None
    date_end: datetime | None
    order_reference: str
    paid_until: datetime | None
    created_at: datetime | None
    purchase_date: datetime | None


def _normalize_status(value: str | None) -> str:
    return (value or "").strip().lower()


def _fmt_dt(value: datetime | None) -> str:
    if not value:
        return "-"
    local_dt = timezone.localtime(value)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def _pick_contact(sub: Subscription) -> tuple[str, str]:
    email = (sub.email or "").strip()
    phone = (sub.phone or "").strip()
    if sub.source_order:
        email = email or (sub.source_order.email or "")
        phone = phone or (sub.source_order.phone or "")
    return email, phone


def _get_purchase_date(sub: Subscription) -> datetime | None:
    if sub.source_order and sub.source_order.created_at:
        return sub.source_order.created_at
    return None


def _add_months(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _estimate_paid_until(sub: Subscription) -> datetime | None:
    if sub.next_payment_date:
        return sub.next_payment_date

    base_date = sub.last_payed_date
    if not base_date and sub.source_order:
        if _normalize_status(sub.source_order.payment_status) in PAID_STATUSES:
            base_date = sub.source_order.created_at
    if not base_date and sub.date_begin:
        base_date = sub.date_begin

    if not base_date:
        return None

    mode = _normalize_status(sub.mode)
    if mode in {"monthly", "month"}:
        return _add_months(base_date, 1)
    if mode in {"quarterly"}:
        return _add_months(base_date, 3)
    if mode in {"yearly", "annual", "annually"}:
        return _add_months(base_date, 12)
    if mode in {"weekly", "week"}:
        return base_date + timedelta(days=7)
    if mode in {"daily", "day"}:
        return base_date + timedelta(days=1)
    return base_date + timedelta(days=30)


def _build_candidates(now: datetime) -> List[RemovalCandidate]:
    qs = Subscription.objects.select_related("source_order").all()
    candidates: list[RemovalCandidate] = []

    for sub in qs:
        status = _normalize_status(sub.status)
        last_payed_status = _normalize_status(sub.last_payed_status)
        next_payment_date = sub.next_payment_date
        paid_until = _estimate_paid_until(sub)

        is_inactive = status in INACTIVE_STATUSES
        is_overdue = (
            next_payment_date is not None
            and next_payment_date < now
            and last_payed_status not in PAID_STATUSES
        )

        if is_inactive and paid_until and paid_until > now:
            # Користувач відмінив підписку, але оплачений період ще діє
            continue

        if not (is_inactive or is_overdue):
            continue

        email, phone = _pick_contact(sub)
        purchase_date = _get_purchase_date(sub)
        candidates.append(
            RemovalCandidate(
                subscription_id=sub.id,
                email=email,
                phone=phone,
                status=sub.status,
                last_payed_status=sub.last_payed_status,
                next_payment_date=sub.next_payment_date,
                date_end=sub.date_end,
                order_reference=sub.order_reference,
                paid_until=paid_until,
                created_at=sub.created_at,
                purchase_date=purchase_date,
            )
        )

    return candidates


def _render_text(candidates: List[RemovalCandidate]) -> str:
    if not candidates:
        return "Кандидатів на видалення немає."

    lines = [
        f"Кандидати на видалення з групи: {len(candidates)}",
        "",
    ]
    for item in candidates:
        lines.append(
            " • ID {id} | {email} | {phone} | status={status} | last={last} | next={next} | end={end} | ref={ref} | paid_until={paid} | purchase={purchase} | created={created}".format(
                id=item.subscription_id,
                email=item.email or "-",
                phone=item.phone or "-",
                status=item.status or "-",
                last=item.last_payed_status or "-",
                next=_fmt_dt(item.next_payment_date),
                end=_fmt_dt(item.date_end),
                ref=item.order_reference or "-",
                paid=_fmt_dt(item.paid_until),
                purchase=_fmt_dt(item.purchase_date),
                created=_fmt_dt(item.created_at),
            )
        )
    return "\n".join(lines)


def _render_html(candidates: List[RemovalCandidate]) -> str:
    if not candidates:
        return "<p>Кандидатів на видалення немає.</p>"

    rows = []
    for item in candidates:
        rows.append(
            "<tr>"
            f"<td>{item.subscription_id}</td>"
            f"<td>{item.email or '-'}</td>"
            f"<td>{item.phone or '-'}</td>"
            f"<td>{item.status or '-'}</td>"
            f"<td>{item.last_payed_status or '-'}</td>"
            f"<td>{_fmt_dt(item.next_payment_date)}</td>"
            f"<td>{_fmt_dt(item.date_end)}</td>"
            f"<td>{item.order_reference or '-'}</td>"
            f"<td>{_fmt_dt(item.paid_until)}</td>"
            f"<td>{_fmt_dt(item.purchase_date)}</td>"
            f"<td>{_fmt_dt(item.created_at)}</td>"
            "</tr>"
        )

    return (
        f"<p>Кандидати на видалення з групи: {len(candidates)}</p>"
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;'>"
        "<thead>"
        "<tr>"
        "<th>ID</th><th>Email</th><th>Телефон</th><th>Статус</th>"
        "<th>Last pay</th><th>Next pay</th><th>End</th><th>OrderRef</th><th>Paid until</th><th>Purchase</th><th>Created</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


class Command(BaseCommand):
    help = "Send email report with subscriptions that should be removed from Telegram group."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            default="rostislav.pas@gmail.com",
            help="Recipient email address.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print report to console instead of sending email.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        candidates = _build_candidates(now)
        text = _render_text(candidates)

        if options["dry_run"]:
            self.stdout.write(text)
            return

        to_email = options["to"]
        subject = "PASUE: кандидати на видалення з Telegram"
        html = _render_html(candidates)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=False)

        self.stdout.write(self.style.SUCCESS(f"Report sent to {to_email}"))
