from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from .models import Deposit, DepositPhoto, Invoice, InvoiceItem, Employee, SystemSettings, StorageBox

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = [
            'visitor_name', 'mobile_number', 'national_id',
            'check_in_date', 'expected_pickup_date',
            'description', 'notes',
            'storage_box', 'storage_location', 'shelf_number',
            'assigned_employee',
        ]
        widgets = {
            'check_in_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'expected_pickup_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'visitor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter visitor name')}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter mobile number')}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter national ID or passport')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Describe the deposit item')}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Additional notes')}),
            'storage_box': forms.Select(attrs={'class': 'form-select'}),
            'storage_location': forms.Select(attrs={'class': 'form-select'}),
            'shelf_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Shelf number')}),
            'assigned_employee': forms.Select(attrs={'class': 'form-select'}),
        }

    photos = MultipleFileField(required=False, label=_('Deposit Photos'))

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer_name', 'customer_phone', 'deposit', 'notes', 'tax_percent']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'deposit': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['service_item', 'quantity', 'unit_price']
        widgets = {
            'service_item': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Service name')}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class EmployeeForm(forms.ModelForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = Employee
        fields = ['full_name', 'phone', 'position', 'employee_id']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = '__all__'
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'tax_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'default_language': forms.Select(attrs={'class': 'form-select'}),
            'default_tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'receipt_footer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'label_size': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DateRangeForm(forms.Form):
    date_from = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_to = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

class BarcodeSearchForm(forms.Form):
    barcode = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': _('Scan or enter barcode...'),
            'id': 'barcode-input',
            'autofocus': True
        }),
        label=''
    )
