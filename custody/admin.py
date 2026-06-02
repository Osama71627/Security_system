from django.contrib import admin
from django.utils.html import format_html
from .models import Deposit, DepositPhoto, Invoice, InvoiceItem, ActivityLog, Employee, Customer, SystemSettings

class DepositPhotoInline(admin.TabularInline):
    model = DepositPhoto
    extra = 1

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ['deposit_number', 'visitor_name', 'mobile_number', 'status', 'payment_status', 'total_amount', 'check_in_date', 'created_at']
    list_filter = ['status', 'payment_status', 'storage_location', 'created_at']
    search_fields = ['deposit_number', 'barcode_number', 'visitor_name', 'mobile_number', 'national_id']
    readonly_fields = ['deposit_number', 'barcode_number', 'created_at', 'updated_at', 'display_qr', 'display_barcode']
    inlines = [DepositPhotoInline]
    list_per_page = 25
    date_hierarchy = 'created_at'

    fieldsets = [
        ('Deposit Info', {'fields': ['deposit_number', 'barcode_number', 'display_barcode', 'display_qr', 'status', 'payment_status']}),
        ('Visitor', {'fields': ['visitor_name', 'mobile_number', 'national_id', 'check_in_date', 'expected_pickup_date']}),
        ('Details', {'fields': ['description', 'notes', 'amount', 'tax_amount', 'total_amount']}),
        ('Storage', {'fields': ['storage_location', 'shelf_number']}),
        ('Assignment', {'fields': ['assigned_employee', 'registered_by']}),
        ('Delivery', {'fields': ['delivery_date', 'delivered_by']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at']}),
    ]

    def display_qr(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return '-'
    display_qr.short_description = 'QR Code'

    def display_barcode(self, obj):
        if obj.barcode_image:
            return format_html('<img src="{}" width="200" height="60" />', obj.barcode_image.url)
        return '-'
    display_barcode.short_description = 'Barcode'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.registered_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer_name', 'total', 'is_paid', 'created_at']
    list_filter = ['is_paid', 'created_at']
    search_fields = ['invoice_number', 'customer_name']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline]

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['mobile', 'full_name', 'created_at']
    search_fields = ['mobile', 'full_name']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'deposit', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'action', 'description']
    readonly_fields = ['user', 'action', 'description', 'deposit', 'ip_address', 'timestamp']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'position', 'phone', 'is_active']
    list_filter = ['position', 'is_active']
    search_fields = ['employee_id', 'full_name', 'phone']

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    pass
