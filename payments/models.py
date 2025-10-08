from django.db import models


class TicketOrder(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'В очікуванні'),
        ('success', 'Успішно'),
        ('failed', 'Неуспішно'),
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
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    ticket_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Активний'),
            ('used', 'Використаний'),
            ('invalid', 'Недійсний'),
        ],
        default='active'
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
    wayforpay_order_reference = models.CharField(max_length=100, blank=True, null=True)

    keycrm_lead_id = models.IntegerField(blank=True, null=True, help_text="ID ліда в KeyCRM")
    keycrm_payment_id = models.IntegerField(blank=True, null=True, help_text="ID платежу в KeyCRM")
    callback_processed = models.BooleanField(default=False, help_text="Чи оброблено callback від WayForPay")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    event_name = models.CharField(max_length=255, default='Grand Opening Party')
    scanned_at = models.DateTimeField(null=True, blank=True)
    scanned_by = models.CharField(max_length=100, blank=True)
    scan_count = models.IntegerField(default=0)

    is_verified = models.BooleanField(default=False, verbose_name='Підтверджено адміном')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='Час підтвердження')
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
    ticket = models.ForeignKey(TicketOrder, on_delete=models.CASCADE, related_name='scan_logs')
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    was_valid = models.BooleanField()
    previous_status = models.CharField(max_length=20)

    class Meta:
        ordering = ['-scanned_at']
        verbose_name = 'Лог сканування'
        verbose_name_plural = 'Логи сканувань'

    def __str__(self):
        return f"Сканування #{self.ticket.id} - {self.scanned_at}"
