import json, csv, io
from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.generic import ListView
from django.db.models import Count, Sum, Q
from django.template.loader import render_to_string
from django.conf import settings

from .models import Deposit, DepositPhoto, Invoice, InvoiceItem, ActivityLog, Employee, Customer, SystemSettings, StorageBox
from .forms import DepositForm, InvoiceForm, InvoiceItemForm, EmployeeForm, SystemSettingsForm, BarcodeSearchForm, DateRangeForm
from .utils import generate_barcode_image, generate_qr_code_image, generate_invoice_pdf, generate_receipt_pdf, generate_label_pdf, log_activity
from .decorators import admin_required

# ─── Helpers ─────────────────────────────────────────────────────────
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

def is_customer(user):
    if not user.is_authenticated:
        return False
    return hasattr(user, 'customer_profile') and user.customer_profile is not None

# ─── Logout ─────────────────────────────────────────────────────────
def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('customer_register')

# ─── Customer Auth ──────────────────────────────────────────────────
def customer_register(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        if not mobile:
            messages.error(request, _('Mobile number is required'))
            return render(request, 'custody/customer_register.html')
        if User.objects.filter(username=mobile).exists():
            user = User.objects.get(username=mobile)
            login(request, user)
            messages.success(request, _('Welcome back!'))
            return redirect('customer_home')
        password = mobile[-6:] if len(mobile) >= 6 else mobile
        user = User.objects.create_user(username=mobile, password=password)
        user.save()
        Customer.objects.create(user=user, mobile=mobile, full_name=full_name or mobile)
        login(request, user)
        messages.success(request, _('Account created! Your password is your mobile last 6 digits.'))
        return redirect('customer_home')
    return render(request, 'custody/customer_register.html')

@login_required
def customer_home(request):
    if is_admin(request.user):
        return redirect('dashboard')
    if not is_customer(request.user):
        return redirect('customer_register')
    customer = request.user.customer_profile
    deposits = Deposit.objects.filter(customer=customer).order_by('-created_at')
    return render(request, 'custody/customer_home.html', {'deposits': deposits, 'customer': customer})

@login_required
def customer_deposit(request):
    if is_admin(request.user):
        return redirect('dashboard')
    if not is_customer(request.user):
        return redirect('customer_register')
    customer = request.user.customer_profile
    if request.method == 'POST':
        description = request.POST.get('description', '')
        notes = request.POST.get('notes', '')
        if not description:
            messages.error(request, _('Please describe the item'))
            return render(request, 'custody/customer_deposit.html', {'customer': customer})
        deposit = Deposit.objects.create(
            customer=customer,
            visitor_name=customer.full_name or customer.mobile,
            mobile_number=customer.mobile,
            national_id='', description=description, notes=notes,
            status='draft', payment_status='pending',
        )
        for f in request.FILES.getlist('photos'):
            DepositPhoto.objects.create(deposit=deposit, image=f)
        available_box = StorageBox.objects.filter(is_available=True).first()
        if available_box:
            deposit.storage_box = available_box
            available_box.is_available = False
            available_box.save()
        settings_obj = SystemSettings.objects.first()
        fee = settings_obj.deposit_fee if settings_obj else 50
        fee_desc = settings_obj.deposit_fee_description if settings_obj else 'Deposit Service Fee'
        tax_pct = settings_obj.default_tax_percent if settings_obj else 15
        subtotal = fee
        tax_amt = subtotal * (tax_pct / Decimal('100'))
        total = subtotal + tax_amt
        invoice = Invoice.objects.create(
            deposit=deposit,
            customer_name=customer.full_name or customer.mobile,
            customer_phone=customer.mobile,
            subtotal=subtotal, tax_percent=tax_pct, tax_amount=tax_amt, total=total,
            created_by=request.user,
        )
        InvoiceItem.objects.create(invoice=invoice, service_item=fee_desc, quantity=1, unit_price=fee, total=fee)
        deposit.amount = subtotal
        deposit.tax_amount = tax_amt
        deposit.total_amount = total
        deposit.save()
        log_activity(request.user, 'Customer submitted deposit', f'{deposit.deposit_number}', deposit, request)
        return redirect('customer_payment', pk=deposit.pk)
    return render(request, 'custody/customer_deposit.html', {'customer': customer})

@login_required
def customer_payment(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    if is_admin(request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        deposit.status = 'paid'
        deposit.payment_status = 'paid'
        barcode_img = generate_barcode_image(deposit.deposit_number)
        if barcode_img:
            deposit.barcode_image.save(f'barcode_{deposit.deposit_number}.png', barcode_img)
        qr_img = generate_qr_code_image(deposit.deposit_number)
        if qr_img:
            deposit.qr_code.save(f'qrcode_{deposit.deposit_number}.png', qr_img)
        deposit.save()
        log_activity(request.user, 'Customer paid', f'{deposit.deposit_number}', deposit, request)
        return redirect('customer_success', pk=deposit.pk)
    invoice = deposit.invoices.filter(is_paid=False).first()
    return render(request, 'custody/customer_payment.html', {'deposit': deposit, 'invoice': invoice})

@login_required
def customer_success(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    return render(request, 'custody/customer_success.html', {'deposit': deposit})

@login_required
def customer_deposit_detail(request, pk):
    deposit = get_object_or_404(Deposit.objects.prefetch_related('photos', 'invoices'), pk=pk)
    if is_admin(request.user):
        return redirect('dashboard')
    customer = request.user.customer_profile
    if deposit.customer != customer:
        messages.error(request, _('This is not your deposit.'))
        return redirect('customer_home')
    return render(request, 'custody/customer_deposit_detail.html', {'deposit': deposit})

@login_required
def customer_invoice_pay(request, pk):
    deposit = get_object_or_404(Deposit.objects.prefetch_related('invoices'), pk=pk)
    if is_admin(request.user):
        return redirect('dashboard')
    customer = request.user.customer_profile
    if deposit.customer != customer:
        return redirect('customer_home')
    invoice = deposit.invoices.filter(is_paid=False).first()
    if request.method == 'POST':
        if invoice:
            invoice.is_paid = True
            invoice.payment_date = timezone.now()
            invoice.payment_method = 'online'
            invoice.save()
        deposit.payment_status = 'paid'
        deposit.status = 'paid'
        barcode_img = generate_barcode_image(deposit.deposit_number)
        if barcode_img:
            deposit.barcode_image.save(f'barcode_{deposit.deposit_number}.png', barcode_img)
        qr_img = generate_qr_code_image(deposit.deposit_number)
        if qr_img:
            deposit.qr_code.save(f'qrcode_{deposit.deposit_number}.png', qr_img)
        deposit.save()
        log_activity(request.user, 'Customer paid invoice', f'{deposit.deposit_number}', deposit, request)
        messages.success(request, _('Payment successful!'))
        return redirect('customer_success', pk=deposit.pk)
    return render(request, 'custody/customer_invoice_pay.html', {'deposit': deposit, 'invoice': invoice})

# ─── Admin Auth ─────────────────────────────────────────────────────
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect('dashboard')
        messages.error(request, _('Invalid credentials or not an admin.'))
    return render(request, 'custody/admin_login.html')

def admin_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        code = request.POST.get('admin_code', '')
        if code != settings.SECRET_KEY[:6]:
            messages.error(request, _('Invalid admin registration code.'))
            return render(request, 'custody/admin_register.html')
        if username and password:
            user = User.objects.create_user(username=username, password=password, is_staff=True)
            login(request, user)
            messages.success(request, _('Admin account created!'))
            return redirect('dashboard')
    return render(request, 'custody/admin_register.html')

# ─── Dashboard ───────────────────────────────────────────────────────
@login_required
def dashboard(request):
    if not is_admin(request.user):
        return redirect('customer_home')
    if not SystemSettings.objects.exists():
        SystemSettings.objects.create()
    context = {
        'total_deposits': Deposit.objects.count(),
        'deposits_today': Deposit.objects.filter(created_at__date=timezone.now().date()).count(),
        'pending_pickup': Deposit.objects.filter(status__in=['draft', 'received', 'invoiced']).count(),
        'delivered_deposits': Deposit.objects.filter(status='delivered').count(),
        'revenue_today': Invoice.objects.filter(created_at__date=timezone.now().date(), is_paid=True).aggregate(t=Sum('total'))['t'] or 0,
        'revenue_month': Invoice.objects.filter(created_at__month=timezone.now().month, created_at__year=timezone.now().year, is_paid=True).aggregate(t=Sum('total'))['t'] or 0,
        'recent_deposits': Deposit.objects.select_related('customer').order_by('-created_at')[:10],
        'recent_activities': ActivityLog.objects.select_related('user', 'deposit').order_by('-timestamp')[:10],
        'status_counts': {
            s[0]: Deposit.objects.filter(status=s[0]).count() for s in Deposit._meta.get_field('status').choices
        },
        'customers_count': Customer.objects.count(),
    }
    return render(request, 'custody/dashboard.html', context)

@login_required
def ajax_dashboard_stats(request):
    return JsonResponse({
        'total_deposits': Deposit.objects.count(),
        'deposits_today': Deposit.objects.filter(created_at__date=timezone.now().date()).count(),
        'pending_pickup': Deposit.objects.filter(status__in=['draft', 'received', 'invoiced']).count(),
        'delivered_deposits': Deposit.objects.filter(status='delivered').count(),
        'revenue_today': float(Invoice.objects.filter(created_at__date=timezone.now().date(), is_paid=True).aggregate(t=Sum('total'))['t'] or 0),
        'revenue_month': float(Invoice.objects.filter(created_at__month=timezone.now().month, created_at__year=timezone.now().year, is_paid=True).aggregate(t=Sum('total'))['t'] or 0),
    })

@login_required
def ajax_recent_activities(request):
    activities = ActivityLog.objects.select_related('user', 'deposit').order_by('-timestamp')[:10]
    html = render_to_string('custody/includes/activity_rows.html', {'activities': activities}, request)
    return JsonResponse({'html': html})

@login_required
def ajax_chart_data(request):
    days = 30
    dates = [(timezone.now().date() - timedelta(days=i)) for i in range(days - 1, -1, -1)]
    daily_deposits = [Deposit.objects.filter(created_at__date=d).count() for d in dates]
    daily_revenue = [float(Invoice.objects.filter(created_at__date=d, is_paid=True).aggregate(t=Sum('total'))['t'] or 0) for d in dates]
    return JsonResponse({
        'dates': [d.strftime('%Y-%m-%d') for d in dates],
        'daily_deposits': daily_deposits,
        'daily_revenue': daily_revenue,
        'status_chart': {
            'labels': [s[1] for s in Deposit._meta.get_field('status').choices],
            'values': [Deposit.objects.filter(status=s[0]).count() for s in Deposit._meta.get_field('status').choices],
        },
        'payment_chart': {
            'labels': ['Paid', 'Pending', 'Partial', 'Refunded'],
            'values': [
                Deposit.objects.filter(payment_status='paid').count(),
                Deposit.objects.filter(payment_status='pending').count(),
                Deposit.objects.filter(payment_status='partial').count(),
                Deposit.objects.filter(payment_status='refunded').count(),
            ],
        },
    })

# ─── Deposits ────────────────────────────────────────────────────────
class DepositListView(ListView):
    model = Deposit
    template_name = 'custody/deposit_list.html'
    context_object_name = 'deposits'
    paginate_by = 25

    def get_queryset(self):
        qs = Deposit.objects.select_related('customer').all()
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        location = self.request.GET.get('location')
        if q:
            qs = qs.filter(Q(deposit_number__icontains=q) | Q(visitor_name__icontains=q) | Q(mobile_number__icontains=q) | Q(barcode_number__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if location:
            qs = qs.filter(storage_location=location)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Deposit._meta.get_field('status').choices
        ctx['location_choices'] = Deposit._meta.get_field('storage_location').choices
        return ctx

@login_required
def deposit_create(request):
    if request.method == 'POST':
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.registered_by = request.user
            deposit.save()
            for f in request.FILES.getlist('photos'):
                DepositPhoto.objects.create(deposit=deposit, image=f)
            barcode_img = generate_barcode_image(deposit.deposit_number)
            if barcode_img:
                deposit.barcode_image.save(f'barcode_{deposit.deposit_number}.png', barcode_img)
            qr_img = generate_qr_code_image(deposit.deposit_number)
            if qr_img:
                deposit.qr_code.save(f'qrcode_{deposit.deposit_number}.png', qr_img)
            deposit.save()
            log_activity(request.user, 'Created Deposit', f'Deposit {deposit.deposit_number} created', deposit, request)
            messages.success(request, _('Deposit created successfully!'))
            return redirect('deposit_detail', pk=deposit.pk)
    else:
        form = DepositForm()
    return render(request, 'custody/deposit_form.html', {'form': form})

@login_required
def deposit_detail(request, pk):
    deposit = get_object_or_404(Deposit.objects.prefetch_related('photos', 'activities__user', 'invoices'), pk=pk)
    status_choices = Deposit._meta.get_field('status').choices
    return render(request, 'custody/deposit_detail.html', {'deposit': deposit, 'status_choices': status_choices})

@login_required
def deposit_edit(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    if request.method == 'POST':
        form = DepositForm(request.POST, request.FILES, instance=deposit)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist('photos'):
                DepositPhoto.objects.create(deposit=deposit, image=f)
            log_activity(request.user, 'Edited Deposit', f'Deposit {deposit.deposit_number} edited', deposit, request)
            messages.success(request, _('Deposit updated!'))
            return redirect('deposit_detail', pk=deposit.pk)
    else:
        form = DepositForm(instance=deposit)
    return render(request, 'custody/deposit_form.html', {'form': form, 'deposit': deposit})

@login_required
def deposit_delete(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    if request.method == 'POST':
        log_activity(request.user, 'Deleted Deposit', f'Deposit {deposit.deposit_number} deleted', None, request)
        deposit.delete()
        messages.success(request, _('Deposit deleted!'))
        return redirect('deposit_list')
    return render(request, 'custody/deposit_confirm_delete.html', {'deposit': deposit})

@login_required
def update_status(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Deposit._meta.get_field('status').choices):
            deposit.status = new_status
            if new_status == 'delivered':
                deposit.delivery_date = timezone.now()
                deposit.delivered_by = request.user
                deposit.payment_status = 'paid'
            deposit.save()
            log_activity(request.user, f'Status changed to {new_status}', f'Deposit {deposit.deposit_number}', deposit, request)
            messages.success(request, _('Status updated!'))
    return redirect('deposit_detail', pk=deposit.pk)

# ─── Barcode Delivery ────────────────────────────────────────────────
@login_required
def barcode_delivery(request):
    if not is_admin(request.user):
        return redirect('customer_home')
    form = BarcodeSearchForm()
    return render(request, 'custody/barcode_delivery.html', {'form': form})

@login_required
def barcode_lookup(request):
    if not is_admin(request.user):
        return JsonResponse({'found': False, 'error': 'Staff only'})
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'found': False, 'error': _('No barcode provided')})
    try:
        deposit = Deposit.objects.select_related('customer').get(
            Q(deposit_number=barcode) | Q(barcode_number=barcode)
        )
        photos = []
        for p in deposit.photos.all()[:3]:
            try:
                photos.append({'url': p.image.url})
            except:
                photos.append({'url': None})
        invoices_data = []
        for inv in deposit.invoices.all():
            invoices_data.append({
                'number': inv.invoice_number,
                'total': str(inv.total),
                'is_paid': inv.is_paid,
            })
        data = {
            'found': True, 'id': deposit.id,
            'deposit_number': deposit.deposit_number, 'visitor_name': deposit.visitor_name,
            'mobile_number': deposit.mobile_number, 'description': deposit.description[:100],
            'status': deposit.status, 'status_display': deposit.get_status_display(),
            'payment_status': deposit.payment_status, 'amount': str(deposit.total_amount),
            'check_in_date': deposit.check_in_date.strftime('%Y-%m-%d %H:%M'),
            'customer_name': str(deposit.customer) if deposit.customer else 'N/A',
            'photos': photos, 'qr_url': deposit.qr_code.url if deposit.qr_code else None,
            'invoices': invoices_data,
        }
        return JsonResponse(data)
    except Deposit.DoesNotExist:
        return JsonResponse({'found': False, 'error': _('Deposit not found')})

@login_required
def confirm_delivery(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Staff only'})
    deposit = get_object_or_404(Deposit, pk=pk)
    if request.method == 'POST':
        deposit.status = 'delivered'
        deposit.delivery_date = timezone.now()
        deposit.delivered_by = request.user
        deposit.payment_status = 'paid'
        if deposit.storage_box:
            deposit.storage_box.is_available = True
            deposit.storage_box.save()
        deposit.save()
        log_activity(request.user, 'Delivered Deposit', f'Deposit {deposit.deposit_number} delivered', deposit, request)
        return JsonResponse({'success': True, 'message': _('Deposit delivered!')})
    return JsonResponse({'success': False, 'error': _('Invalid request')})

# ─── Invoices ────────────────────────────────────────────────────────
class InvoiceListView(ListView):
    model = Invoice
    template_name = 'custody/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25
    def get_queryset(self):
        qs = Invoice.objects.all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(invoice_number__icontains=q) | Q(customer_name__icontains=q))
        return qs

@login_required
def invoice_create(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.subtotal = 0; invoice.tax_amount = 0; invoice.total = 0
            invoice.save()
            subtotal = 0
            for i, name in enumerate(request.POST.getlist('service_item[]')):
                if name:
                    qty = int(request.POST.getlist('quantity[]')[i]) if request.POST.getlist('quantity[]')[i] else 1
                    price = float(request.POST.getlist('unit_price[]')[i]) if request.POST.getlist('unit_price[]')[i] else 0
                    t = qty * price
                    InvoiceItem.objects.create(invoice=invoice, service_item=name, quantity=qty, unit_price=price, total=t)
                    subtotal += t
            tax = subtotal * (invoice.tax_percent / Decimal('100'))
            invoice.subtotal = subtotal; invoice.tax_amount = tax; invoice.total = subtotal + tax
            invoice.save()
            if invoice.deposit:
                invoice.deposit.status = 'invoiced'
                invoice.deposit.amount = invoice.subtotal
                invoice.deposit.tax_amount = invoice.tax_amount
                invoice.deposit.total_amount = invoice.total
                invoice.deposit.save()
            log_activity(request.user, 'Created Invoice', f'Invoice {invoice.invoice_number}', invoice.deposit, request)
            messages.success(request, _('Invoice created!'))
            return redirect('invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm()
    return render(request, 'custody/invoice_form.html', {'form': form})

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('items'), pk=pk)
    return render(request, 'custody/invoice_detail.html', {'invoice': invoice})

@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('items'), pk=pk)
    settings_obj = SystemSettings.objects.first()
    pdf_buffer = generate_invoice_pdf(invoice, settings_obj)
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="INV_{invoice.invoice_number}.pdf"'
    return response

@login_required
def mark_invoice_paid(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.is_paid = True
        invoice.payment_date = timezone.now()
        invoice.payment_method = request.POST.get('payment_method', 'cash')
        invoice.save()
        if invoice.deposit:
            invoice.deposit.payment_status = 'paid'
            invoice.deposit.status = 'paid'
            invoice.deposit.save()
        log_activity(request.user, 'Payment Received', f'Invoice {invoice.invoice_number} paid', invoice.deposit, request)
        messages.success(request, _('Payment recorded!'))
    return redirect('invoice_detail', pk=invoice.pk)

# ─── Receipts & Labels ───────────────────────────────────────────────
@login_required
def deposit_receipt(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    pdf_buffer = generate_receipt_pdf(deposit, SystemSettings.objects.first())
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Receipt_{deposit.deposit_number}.pdf"'
    return response

@login_required
def deposit_label(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    w = int(request.GET.get('width', 50))
    h = int(request.GET.get('height', 30))
    pdf_buffer = generate_label_pdf(deposit, w, h, SystemSettings.objects.first())
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Label_{deposit.deposit_number}.pdf"'
    return response

# ─── Search & Reports ────────────────────────────────────────────────
@login_required
def search_deposits(request):
    qs = Deposit.objects.select_related('customer').all()
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    location = request.GET.get('location', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if query:
        qs = qs.filter(Q(deposit_number__icontains=query) | Q(barcode_number__icontains=query) | Q(visitor_name__icontains=query) | Q(mobile_number__icontains=query) | Q(national_id__icontains=query))
    if status: qs = qs.filter(status=status)
    if location: qs = qs.filter(storage_location=location)
    if date_from: qs = qs.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to: qs = qs.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
    return render(request, 'custody/search.html', {
        'results': qs[:50], 'count': qs.count(), 'query': query,
        'status_choices': Deposit._meta.get_field('status').choices,
        'location_choices': Deposit._meta.get_field('storage_location').choices,
    })

@login_required
def reports_view(request):
    form = DateRangeForm(request.GET or None)
    return render(request, 'custody/reports.html', {
        'form': form,
        'date_from': request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
        'date_to': request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d')),
    })

@login_required
def export_report(request):
    report_type = request.GET.get('type', 'daily')
    fmt = request.GET.get('format', 'csv')
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
    deposits = Deposit.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    if report_type == 'daily': deposits = deposits.filter(created_at__date=timezone.now().date())
    elif report_type == 'pending': deposits = deposits.filter(status__in=['draft', 'received', 'invoiced', 'paid'])
    elif report_type == 'delivered': deposits = deposits.filter(status='delivered')
    elif report_type == 'revenue':
        invoices = Invoice.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        if fmt == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="revenue_report_{date_from}_{date_to}.csv"'
            w = csv.writer(response)
            w.writerow(['Invoice', 'Customer', 'Total', 'Tax', 'Date', 'Paid'])
            for inv in invoices:
                w.writerow([inv.invoice_number, inv.customer_name, inv.total, inv.tax_amount, inv.created_at.date(), 'Yes' if inv.is_paid else 'No'])
            return response
    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{date_from}_{date_to}.csv"'
        w = csv.writer(response)
        w.writerow(['Deposit No', 'Visitor', 'Mobile', 'Status', 'Amount', 'Date'])
        for d in deposits:
            w.writerow([d.deposit_number, d.visitor_name, d.mobile_number, d.get_status_display(), d.total_amount, d.created_at.date()])
        return response
    elif fmt == 'pdf':
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        pdf = io.BytesIO()
        p = canvas.Canvas(pdf, pagesize=A4)
        w2, h = A4
        p.setFont('Helvetica-Bold', 16)
        p.drawString(50, h - 50, f'{report_type.title()} Report')
        p.setFont('Helvetica', 10)
        y = h - 80
        for d in deposits:
            p.drawString(50, y, f'{d.deposit_number} - {d.visitor_name} - {d.mobile_number} - {d.get_status_display()} - {d.total_amount}')
            y -= 15
            if y < 50: p.showPage(); y = h - 50
        p.showPage(); p.save()
        response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{date_from}_{date_to}.pdf"'
        return response
    return redirect('reports')

# ─── Activity Log ────────────────────────────────────────────────────
@login_required
def activity_log_view(request):
    logs = ActivityLog.objects.select_related('user', 'deposit').all().order_by('-timestamp')[:100]
    return render(request, 'custody/activity_log.html', {'logs': logs})

# ─── Admin Management ────────────────────────────────────────────────
@login_required
@admin_required
def admin_list(request):
    admins = User.objects.filter(is_staff=True).order_by('username')
    return render(request, 'custody/admin_list.html', {'admins': admins})

@login_required
@admin_required
def admin_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and password:
            User.objects.create_user(username=username, password=password, is_staff=True)
            messages.success(request, _('Admin added!'))
            return redirect('admin_list')
    return render(request, 'custody/admin_form.html')

# ─── Customer Management (Admin) ────────────────────────────────────
@login_required
@admin_required
def customer_list(request):
    customers = Customer.objects.select_related('user').all().order_by('-created_at')
    return render(request, 'custody/customer_list.html', {'customers': customers})

# ─── Storage Box Management (Admin) ─────────────────────────────────
@login_required
@admin_required
def storage_box_list(request):
    boxes = StorageBox.objects.all().order_by('box_number')
    return render(request, 'custody/storage_box_list.html', {'boxes': boxes})

@login_required
@admin_required
def storage_box_create(request):
    if request.method == 'POST':
        box_number = request.POST.get('box_number', '').strip()
        description = request.POST.get('description', '').strip()
        location_area = request.POST.get('location_area', '').strip()
        if box_number:
            StorageBox.objects.create(box_number=box_number, description=description, location_area=location_area, is_available=True)
            messages.success(request, _('Storage box added!'))
            return redirect('storage_box_list')
        messages.error(request, _('Box number is required'))
    return render(request, 'custody/storage_box_form.html')

@login_required
@admin_required
def storage_box_toggle(request, pk):
    box = get_object_or_404(StorageBox, pk=pk)
    box.is_available = not box.is_available
    box.save()
    messages.success(request, _('Box status updated!'))
    return redirect('storage_box_list')

@login_required
@admin_required
def storage_box_delete(request, pk):
    box = get_object_or_404(StorageBox, pk=pk)
    box.delete()
    messages.success(request, _('Box deleted!'))
    return redirect('storage_box_list')

# ─── System Settings ────────────────────────────────────────────────
@login_required
@admin_required
def system_settings_view(request):
    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, _('Settings saved!'))
            return redirect('settings')
    else:
        form = SystemSettingsForm(instance=settings_obj)
    return render(request, 'custody/settings.html', {'form': form})
