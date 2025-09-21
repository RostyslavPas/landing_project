from django.db import models
from django.utils import timezone


class TicketOrder(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Очікує оплати'),
        ('success', 'Оплачено'),
        ('failed', 'Помилка оплати'),
        ('cancelled', 'Скасовано'),
    ]

    EMAIL_STATUS_CHOICES = [
        ('not_sent', 'Не відправлено'),
        ('sent', 'Відправлено'),
        ('failed', 'Помилка відправки'),
    ]

    DEVICE_TYPE_CHOICES = [
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
    ]

    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Номер телефону")
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="Статус оплати"
    )
    email_status = models.CharField(
        max_length=20,
        choices=EMAIL_STATUS_CHOICES,
        default='not_sent',
        verbose_name="Статус відправки листа"
    )
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPE_CHOICES,
        verbose_name="Тип пристрою"
    )
    wayforpay_order_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Номер замовлення WayForPay"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1789.00,
        verbose_name="Сума"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата створення")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата оновлення")

    class Meta:
        verbose_name = "Замовлення квитка"
        verbose_name_plural = "Замовлення квитків"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {self.payment_status}"
    