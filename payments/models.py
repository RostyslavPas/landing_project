from django.db import models

class Order(models.Model):
    product_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="UAH")
    status = models.CharField(max_length=50, default="created")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} - {self.amount} {self.currency} ({self.status})"
