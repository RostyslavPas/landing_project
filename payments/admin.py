from django.contrib import admin
from .models import TicketOrder


@admin.register(TicketOrder)
class TicketOrderAdmin(admin.ModelAdmin):
    list_display = [
        'email',
        'phone',
        'payment_status',
        'email_status',
        'device_type',
        'amount',
        'wayforpay_order_reference',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'payment_status',
        'email_status',
        'device_type',
        'created_at'
    ]
    search_fields = ['email', 'phone', 'wayforpay_order_reference']
    readonly_fields = ['created_at', 'updated_at', 'wayforpay_order_reference']

    fieldsets = (
        ('Контактна інформація', {
            'fields': ('email', 'phone', 'device_type')
        }),
        ('Платіжна інформація', {
            'fields': ('amount', 'payment_status', 'wayforpay_order_reference')
        }),
        ('Email статус', {
            'fields': ('email_status',)
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['email', 'phone', 'device_type']
        return self.readonly_fields
