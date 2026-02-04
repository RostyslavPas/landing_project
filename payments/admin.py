from django.contrib import admin
from .models import TicketScanLog, SubscriptionOrder, Subscription, Event, TicketOrder
from django.utils.html import format_html


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "location", "price", "max_tickets", "is_active")
    list_editable = ("is_active",)
    search_fields = ("title",)
    ordering = ("-date",)


@admin.register(TicketOrder)
class TicketOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'email',
        'phone',
        'ticket_number',
        'event',
        'payment_status',
        'email_status',
        'device_type',
        'amount',
        'wayforpay_order_reference',
        'created_at',
        'ticket_status',
        'is_verified_badge'
    ]
    list_filter = [
        'payment_status',
        'ticket_status',
        'is_verified',
        'email_status',
        'device_type',
        'created_at'
    ]
    search_fields = ['id', 'name', 'email', 'phone', 'wayforpay_order_reference']
    readonly_fields = ['created_at', 'updated_at', 'wayforpay_order_reference', 'verified_at', 'verified_by', 'scanned_at', 'scanned_by', 'scan_count']

    fieldsets = (
        ('Контактна інформація', {
            'fields': ('name', 'email', 'phone', 'device_type')
        }),
        ('Платіжна інформація', {
            'fields': ('amount', 'payment_status', 'wayforpay_order_reference')
        }),
        ('Cтатус квитка', {
            'fields': ('ticket_status', 'scanned_at', 'scanned_by', 'scan_count')
        }),
        ('Підтвердження адміном', {
            'fields': ('is_verified', 'verified_at', 'verified_by'),
            'classes': ('collapse',)
        }),
        ('Email статус', {
            'fields': ('email_status',)
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at', 'keycrm_lead_id'),
            'classes': ('collapse',)
        }),
    )

    actions = ['verify_tickets', 'unverify_tickets']

    def is_verified_badge(self, obj):
        """Відображення статусу підтвердження"""
        if obj.is_verified:
            return format_html(
                '<span style="color: white; background: #4CAF50; padding: 5px 10px; '
                'border-radius: 10px; font-weight: bold;">✓ Підтверджено</span>'
            )
        return format_html(
            '<span style="color: white; background: #FF9800; padding: 5px 10px; '
            'border-radius: 10px; font-weight: bold;">⏳ Очікує</span>'
        )
    is_verified_badge.short_description = 'Підтвердження'

    def verify_tickets(self, request, queryset):
        """Масове підтвердження квитків"""
        count = 0
        for ticket in queryset.filter(payment_status='success', is_verified=False):
            ticket.verify_ticket(request.user)
            count += 1

        self.message_user(request, f'Підтверджено квитків: {count}')

    verify_tickets.short_description = '✓ Підтвердити вибрані квитки'

    def unverify_tickets(self, request, queryset):
        """Скасування підтвердження"""
        count = queryset.update(is_verified=False, verified_at=None, verified_by=None)
        self.message_user(request, f'Скасовано підтвердження: {count} квитків')

    unverify_tickets.short_description = '✗ Скасувати підтвердження'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['name', 'email', 'phone', 'device_type']
        return self.readonly_fields


@admin.register(TicketScanLog)
class TicketScanLogAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'scanned_at', 'was_valid', 'scanned_by', 'ip_address']
    list_filter = ['was_valid', 'scanned_at']
    readonly_fields = ['ticket', 'scanned_at', 'scanned_by', 'ip_address', 'was_valid', 'previous_status']

    def ticket_id(self, obj):
        return f"#{obj.ticket.id}"

    ticket_id.short_description = 'Квиток'


@admin.register(SubscriptionOrder)
class SubscriptionOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'email',
        'wfp_email',
        'phone',
        'payment_status',
        'device_type',
        'utm_source',
        'created_at'
    ]
    list_filter = [
        'payment_status',
        'device_type',
        'utm_source',
        'utm_medium',
        'utm_campaign',
        'created_at'
    ]
    search_fields = [
        'name',
        'email',
        'phone',
        'wayforpay_order_reference',
        'utm_source',
        'utm_campaign',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'utm_source',
        'utm_medium',
        'utm_campaign',
        'utm_term',
        'utm_content',
        'wfp_name',
        'wfp_email',
        'wfp_phone',
    ]
    ordering = ['-created_at']

    # ✅ Групування полів
    fieldsets = (
        ('Контактна інформація', {
            'fields': ('name', 'email', 'phone', 'device_type')
        }),
        ('Статус', {
            'fields': ('payment_status', 'wayforpay_order_reference')
        }),
        ('WayForPay контакт', {
            'fields': ('wfp_name', 'wfp_email', 'wfp_phone'),
            'classes': ('collapse',)
        }),
        ('UTM мітки', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'),
            'classes': ('collapse',)
        }),
        ('KeyCRM', {
            'fields': ('keycrm_lead_id', 'keycrm_payment_id', 'keycrm_contact_id'),
            'classes': ('collapse',)
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at', 'callback_processed'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'email',
        'phone',
        'purchase_date',
        'status',
        'mode',
        'next_payment_date',
        'last_payed_date',
        'created_at',
        'last_sync_at',
    ]
    list_filter = ['status', 'mode', 'currency', 'last_sync_at']
    search_fields = ['email', 'phone', 'order_reference']
    readonly_fields = ['order_reference', 'created_at', 'updated_at', 'last_sync_at', 'last_sync_raw']
    ordering = ['-updated_at']

    @admin.display(description="Оплата (Created)", ordering="source_order__created_at")
    def purchase_date(self, obj):
        if obj.source_order and obj.source_order.created_at:
            return obj.source_order.created_at
        return None
