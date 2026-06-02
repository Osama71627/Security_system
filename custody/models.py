import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

DEPOSIT_STATUS = [
    ('draft', _('Draft')),
    ('received', _('Received')),
    ('invoiced', _('Invoiced')),
    ('paid', _('Paid')),
    ('delivered', _('Delivered')),
]

PAYMENT_STATUS = [
    ('pending', _('Pending')),
    ('paid', _('Paid')),
    ('partial', _('Partial')),
    ('refunded', _('Refunded')),
]

STORAGE_LOCATIONS = [
    ('shelf_a1', _('Shelf A1')),
    ('shelf_a2', _('Shelf A2')),
    ('shelf_b1', _('Shelf B1')),
    ('shelf_b2', _('Shelf B2')),
    ('shelf_c1', _('Shelf C1')),
    ('shelf_c2', _('Shelf C2')),
    ('vault', _('Vault')),
    ('cold_storage', _('Cold Storage')),
]

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    full_name = models.CharField(_('Full Name'), max_length=200, blank=True, null=True)
    mobile = models.CharField(_('Mobile'), max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')

    def __str__(self):
        return f"{self.full_name or self.mobile}"

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(_('Employee ID'), max_length=50, unique=True)
    full_name = models.CharField(_('Full Name'), max_length=200)
    phone = models.CharField(_('Phone'), max_length=20)
    position = models.CharField(_('Position'), max_length=100, choices=[
        ('admin', _('Admin')),
        ('manager', _('Manager')),
        ('receptionist', _('Receptionist')),
        ('cashier', _('Cashier')),
        ('storage', _('Storage Staff')),
    ])
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

class StorageBox(models.Model):
    box_number = models.CharField(_('Box/Unit Number'), max_length=50, unique=True)
    description = models.CharField(_('Description'), max_length=200, blank=True, null=True)
    location_area = models.CharField(_('Location Area'), max_length=100, blank=True, null=True)
    is_available = models.BooleanField(_('Available'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Storage Box')
        verbose_name_plural = _('Storage Boxes')
        ordering = ['box_number']

    def __str__(self):
        return f"{self.box_number} ({self.location_area})" if self.location_area else self.box_number

class Deposit(models.Model):
    deposit_number = models.CharField(_('Deposit Number'), max_length=20, unique=True, editable=False)
    barcode_number = models.CharField(_('Barcode'), max_length=100, unique=True, blank=True, null=True)
    qr_code = models.ImageField(_('QR Code'), upload_to='qrcodes/', blank=True, null=True)
    barcode_image = models.ImageField(_('Barcode Image'), upload_to='barcodes/', blank=True, null=True)

    visitor_name = models.CharField(_('Visitor Name'), max_length=200)
    mobile_number = models.CharField(_('Mobile Number'), max_length=20)
    national_id = models.CharField(_('National ID / Passport'), max_length=50)
    check_in_date = models.DateTimeField(_('Check-In Date'), default=timezone.now)
    expected_pickup_date = models.DateField(_('Expected Pickup Date'), null=True, blank=True)

    description = models.TextField(_('Deposit Description'))
    notes = models.TextField(_('Notes'), blank=True, null=True)

    storage_box = models.ForeignKey(StorageBox, on_delete=models.SET_NULL, null=True, blank=True, related_name='deposits', verbose_name=_('Storage Box'))
    storage_location = models.CharField(_('Storage Location'), max_length=50, choices=STORAGE_LOCATIONS, default='shelf_a1')
    shelf_number = models.CharField(_('Shelf Number'), max_length=50, blank=True, null=True)

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='deposits', verbose_name=_('Customer'))
    assigned_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Assigned Employee'))
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_deposits')

    status = models.CharField(_('Status'), max_length=20, choices=DEPOSIT_STATUS, default='draft')
    payment_status = models.CharField(_('Payment Status'), max_length=20, choices=PAYMENT_STATUS, default='pending')

    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('Tax'), max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(_('Total'), max_digits=10, decimal_places=2, default=0)

    delivery_date = models.DateTimeField(_('Delivery Date'), null=True, blank=True)
    delivered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivered_deposits')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Deposit')
        verbose_name_plural = _('Deposits')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.deposit_number} - {self.visitor_name}"

    def save(self, *args, **kwargs):
        if not self.deposit_number:
            self.deposit_number = self.generate_deposit_number()
        if not self.barcode_number:
            self.barcode_number = self.deposit_number
        super().save(*args, **kwargs)

    def generate_deposit_number(self):
        prefix = 'DEP'
        date_part = timezone.now().strftime('%Y%m%d')
        last = Deposit.objects.filter(deposit_number__startswith=f'{prefix}-{date_part}').count() + 1
        return f'{prefix}-{date_part}-{last:04d}'

class DepositPhoto(models.Model):
    deposit = models.ForeignKey(Deposit, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(_('Image'), upload_to='photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Deposit Photo')
        verbose_name_plural = _('Deposit Photos')

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('User'))
    deposit = models.ForeignKey(Deposit, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    action = models.CharField(_('Action'), max_length=200)
    description = models.TextField(_('Description'), blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"

class Invoice(models.Model):
    invoice_number = models.CharField(_('Invoice Number'), max_length=20, unique=True, editable=False)
    deposit = models.ForeignKey(Deposit, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    customer_name = models.CharField(_('Customer Name'), max_length=200)
    customer_phone = models.CharField(_('Customer Phone'), max_length=20, blank=True, null=True)

    is_paid = models.BooleanField(_('Is Paid'), default=False)
    payment_date = models.DateTimeField(_('Payment Date'), null=True, blank=True)
    payment_method = models.CharField(_('Payment Method'), max_length=50, blank=True, null=True)

    subtotal = models.DecimalField(_('Subtotal'), max_digits=10, decimal_places=2, default=0)
    tax_percent = models.DecimalField(_('Tax %'), max_digits=5, decimal_places=2, default=15)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_('Total'), max_digits=10, decimal_places=2, default=0)

    notes = models.TextField(_('Notes'), blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    def generate_invoice_number(self):
        prefix = 'INV'
        date_part = timezone.now().strftime('%Y%m%d')
        last = Invoice.objects.filter(invoice_number__startswith=f'{prefix}-{date_part}').count() + 1
        return f'{prefix}-{date_part}-{last:04d}'

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service_item = models.CharField(_('Service Item'), max_length=200)
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    unit_price = models.DecimalField(_('Unit Price'), max_digits=10, decimal_places=2)
    total = models.DecimalField(_('Total'), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('Invoice Item')
        verbose_name_plural = _('Invoice Items')

class SystemSettings(models.Model):
    company_name = models.CharField(_('Company Name'), max_length=200, default='Custody Management')
    company_logo = models.ImageField(_('Company Logo'), upload_to='logos/', blank=True, null=True)
    address = models.TextField(_('Address'), blank=True, null=True)
    phone = models.CharField(_('Phone'), max_length=20, blank=True, null=True)
    email = models.EmailField(_('Email'), blank=True, null=True)
    tax_registration = models.CharField(_('Tax Registration'), max_length=100, blank=True, null=True)
    currency = models.CharField(_('Currency'), max_length=10, default='SAR')
    default_language = models.CharField(_('Default Language'), max_length=10, choices=[('en', 'English'), ('ar', 'Arabic')], default='en')
    default_tax_percent = models.DecimalField(_('Default Tax %'), max_digits=5, decimal_places=2, default=15)
    receipt_footer = models.TextField(_('Receipt Footer'), blank=True, null=True)
    label_size = models.CharField(_('Label Size'), max_length=20, default='50x30')
    deposit_fee = models.DecimalField(_('Deposit Fee'), max_digits=10, decimal_places=2, default=50.00)
    deposit_fee_description = models.CharField(_('Fee Description'), max_length=200, default='Deposit Service Fee')

    class Meta:
        verbose_name = _('System Settings')
        verbose_name_plural = _('System Settings')

    def __str__(self):
        return self.company_name
