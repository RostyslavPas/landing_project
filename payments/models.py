from django.db import models
import uuid


class Event(models.Model):
    title = models.CharField(
        max_length=255,
        default="PASUE Club - Grand Opening Party",
        verbose_name="Назва події"
    )
    date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата проведення"
    )
    time = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Час проведення",
        help_text="Наприклад: 17:00-20:00"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Місце проведення"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1559.00,
        verbose_name="Ціна квитка"
    )
    max_tickets = models.PositiveIntegerField(
        default=50,
        verbose_name="Ліміт квитків"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна подія",
        help_text="Позначити поточну подію як активну"
    )

    def __str__(self):
        return f"{self.title} ({self.date})"


class TicketOrder(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'In pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('expired', 'Expired')
    ]

    EMAIL_STATUS_CHOICES = [
        ('not_sent', 'Не надіслано'),
        ('sent', 'Надіслано'),
        ('failed', 'Помилка відправки'),
    ]

    DEVICE_TYPE_CHOICES = [
        ('desktop', 'Десктоп'),
        ('mobile', 'Мобільний'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1559.00
    )
    ticket_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Активний'),
            ('used', 'Використаний'),
            ('invalid', 'Недійсний'),
        ],
        default='active'
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Подія"
    )
    ticket_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Номер квитка"
    )

    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPE_CHOICES,
        default='desktop'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    email_status = models.CharField(
        max_length=20,
        choices=EMAIL_STATUS_CHOICES,
        default='not_sent'
    )
    wayforpay_order_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    keycrm_lead_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID ліда в KeyCRM"
    )
    keycrm_payment_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID платежу в KeyCRM"
    )
    keycrm_contact_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID контакту в KeyCRM"
    )
    callback_processed = models.BooleanField(
        default=False,
        help_text="Чи оброблено callback від WayForPay"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    event_name = models.CharField(
        max_length=255,
        default='Grand Opening Party'
    )
    scanned_at = models.DateTimeField(
        null=True,
        blank=True
    )
    scanned_by = models.CharField(
        max_length=100,
        blank=True
    )
    scan_count = models.IntegerField(default=0)

    is_verified = models.BooleanField(
        default=False,
        verbose_name='Підтверджено адміном'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Час підтвердження'
    )
    verified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_tickets',
        verbose_name='Підтверджено користувачем'
    )

    def verify_ticket(self, admin_user):
        """Підтверджує квиток"""
        from django.utils import timezone
        self.is_verified = True
        self.verified_at = timezone.now()
        self.verified_by = admin_user
        self.save()

    def mark_as_used(self, scanned_by=''):
        """Відмічає квиток як використаний"""
        from django.utils import timezone
        self.ticket_status = 'used'
        self.scanned_at = timezone.now()
        self.scanned_by = scanned_by
        self.scan_count += 1
        self.save()

    def is_valid(self):
        """Перевіряє чи квиток дійсний"""
        return self.ticket_status == 'active'

    def __str__(self):
        return f"Order #{self.id} - {self.email}"

    class Meta:
        ordering = ['-created_at']


class TicketScanLog(models.Model):
    """Лог сканувань квитків"""
    ticket = models.ForeignKey(
        TicketOrder,
        on_delete=models.CASCADE,
        related_name='scan_logs'
    )
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = models.CharField(
        max_length=100,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    was_valid = models.BooleanField()
    previous_status = models.CharField(max_length=20)

    class Meta:
        ordering = ['-scanned_at']
        verbose_name = 'Лог сканування'
        verbose_name_plural = 'Логи сканувань'

    def __str__(self):
        return f"Сканування #{self.ticket.id} - {self.scanned_at}"


class SubscriptionOrder(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'В очікуванні'),
        ('success', 'Успішно'),
        ('failed', 'Неуспішно'),
    ]

    DEVICE_TYPE_CHOICES = [
        ('desktop', 'Десктоп'),
        ('mobile', 'Мобільний'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPE_CHOICES,
        default='desktop'
    )
    wayforpay_order_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    keycrm_lead_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID ліда в KeyCRM"
    )
    keycrm_payment_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID платежу в KeyCRM"
    )
    keycrm_contact_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID контакту в KeyCRM"
    )
    callback_processed = models.BooleanField(
        default=False,
        help_text="Чи оброблено callback від WayForPay"
    )
    wfp_email = models.EmailField(
        blank=True,
        default='',
        verbose_name="Email (WayForPay)"
    )
    wfp_phone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name="Телефон (WayForPay)"
    )
    wfp_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Імʼя (WayForPay)"
    )

    # ✅ UTM мітки
    utm_source = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='UTM Source',
        help_text='Джерело трафіку'
    )
    utm_medium = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='UTM Medium',
        help_text='Канал трафіку'
    )
    utm_campaign = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='UTM Campaign',
        help_text='Назва кампанії'
    )
    utm_term = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='UTM Term',
        help_text='Ключове слово'
    )
    utm_content = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='UTM Content',
        help_text='Варіант оголошення'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Замовлення підписки"
        verbose_name_plural = "Замовлення підписок"
        ordering = ['-created_at']

    def __str__(self):
        return f"Підписка #{self.id} - {self.name} ({self.email})"


class BotAccessToken(models.Model):
    token = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    order = models.ForeignKey('payments.TicketOrder', on_delete=models.CASCADE, related_name='bot_tokens')
    funnel_tag = models.CharField(max_length=100, default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.token} → {self.order.email} ({self.funnel_tag})"


class SubscriptionBotAccessToken(models.Model):
    token = models.CharField(
        max_length=50,
        unique=True,
        default=uuid.uuid4,
    )
    subscription = models.ForeignKey(
        'payments.SubscriptionOrder',
        on_delete=models.CASCADE,
        related_name='bot_tokens',
    )
    funnel_tag = models.CharField(max_length=100, default='subscription-default')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.token} → {self.subscription.email} ({self.funnel_tag})"


class Subscription(models.Model):
    """Актуальний стан регулярної підписки (синхронізується з WayForPay)."""

    STATUS_CHOICES = [
        ('created', 'Created'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('removed', 'Removed'),
        ('completed', 'Completed'),
        ('unknown', 'Unknown'),
    ]

    order_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="OrderReference першого платежу, під яким створена регулярка в WayForPay",
        verbose_name="WayForPay OrderReference",
    )

    source_order = models.ForeignKey(
        'payments.SubscriptionOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name="Початкове замовлення",
    )

    name = models.CharField(max_length=100, blank=True, default='', verbose_name="Імʼя")
    email = models.EmailField(blank=True, default='', verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name="Телефон")

    mode = models.CharField(max_length=32, blank=True, default='', verbose_name="Regular mode")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Сума")
    currency = models.CharField(max_length=8, blank=True, default='', verbose_name="Валюта")

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='unknown',
        db_index=True,
        verbose_name="Статус",
    )

    date_begin = models.DateTimeField(null=True, blank=True, verbose_name="Початок")
    date_end = models.DateTimeField(null=True, blank=True, verbose_name="Завершення")
    last_payed_date = models.DateTimeField(null=True, blank=True, verbose_name="Останній платіж")
    last_payed_status = models.CharField(max_length=64, blank=True, default='', verbose_name="Статус останнього платежу")
    next_payment_date = models.DateTimeField(null=True, blank=True, verbose_name="Наступний платіж")

    last_reason = models.CharField(max_length=255, blank=True, default='', verbose_name="Причина/повідомлення")
    last_reason_code = models.IntegerField(null=True, blank=True, verbose_name="Reason code")

    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name="Остання синхронізація")
    last_sync_raw = models.JSONField(null=True, blank=True, verbose_name="Остання відповідь WayForPay (raw)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Підписка"
        verbose_name_plural = "Підписки"
        ordering = ['-updated_at']

    def __str__(self):
        label = self.email or self.phone or self.order_reference
        return f"{label} — {self.get_status_display()}"
