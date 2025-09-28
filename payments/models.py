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

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.email}"

    class Meta:
        ordering = ['-created_at']
