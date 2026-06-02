import io
import os
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4, mm
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm as rl_mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.utils import timezone

def generate_barcode_image(deposit_number):
    try:
        rv = io.BytesIO()
        Code128(deposit_number, writer=ImageWriter()).write(rv)
        return ContentFile(rv.getvalue(), name=f'barcode_{deposit_number}.png')
    except Exception as e:
        print(f"Barcode generation error: {e}")
        return None

def generate_qr_code_image(deposit_number):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(deposit_number)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        rv = io.BytesIO()
        img.save(rv, format='PNG')
        return ContentFile(rv.getvalue(), name=f'qrcode_{deposit_number}.png')
    except Exception as e:
        print(f"QR generation error: {e}")
        return None

def generate_invoice_pdf(invoice, settings_obj=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    company_name = settings_obj.company_name if settings_obj else 'Custody Management'
    currency = settings_obj.currency if settings_obj else 'SAR'

    p.setFont('Helvetica-Bold', 20)
    p.drawString(50, height - 50, company_name)
    p.setFont('Helvetica', 10)

    if settings_obj and settings_obj.address:
        p.drawString(50, height - 70, settings_obj.address)
    if settings_obj and settings_obj.phone:
        p.drawString(50, height - 85, f'Tel: {settings_obj.phone}')
    if settings_obj and settings_obj.email:
        p.drawString(50, height - 100, f'Email: {settings_obj.email}')
    if settings_obj and settings_obj.tax_registration:
        p.drawString(50, height - 115, f'Tax Reg: {settings_obj.tax_registration}')

    p.setFont('Helvetica-Bold', 16)
    p.drawString(50, height - 150, 'INVOICE')
    p.setFont('Helvetica', 11)
    p.drawString(50, height - 170, f'Invoice No: {invoice.invoice_number}')
    p.drawString(50, height - 185, f'Date: {invoice.created_at.strftime("%Y-%m-%d %H:%M")}')
    p.drawString(50, height - 200, f'Customer: {invoice.customer_name}')
    if invoice.customer_phone:
        p.drawString(50, height - 215, f'Phone: {invoice.customer_phone}')

    y = height - 250
    p.setFont('Helvetica-Bold', 10)
    p.drawString(50, y, 'Item')
    p.drawString(300, y, 'Qty')
    p.drawString(350, y, 'Price')
    p.drawString(450, y, 'Total')

    p.setStrokeColor(colors.black)
    p.line(50, y - 5, 520, y - 5)
    p.setFont('Helvetica', 10)

    y -= 20
    for item in invoice.items.all():
        p.drawString(50, y, item.service_item[:35])
        p.drawString(300, y, str(item.quantity))
        p.drawString(350, y, f'{item.unit_price:.2f}')
        p.drawString(450, y, f'{item.total:.2f}')
        y -= 20

    y -= 10
    p.line(50, y, 520, y)
    y -= 20
    p.drawString(350, y, f'Subtotal: {invoice.subtotal:.2f} {currency}')
    y -= 15
    p.drawString(350, y, f'Tax ({invoice.tax_percent}%): {invoice.tax_amount:.2f} {currency}')
    y -= 15
    p.setFont('Helvetica-Bold', 12)
    p.drawString(350, y, f'Total: {invoice.total:.2f} {currency}')

    y -= 30
    p.setFont('Helvetica', 9)
    p.drawString(50, y, f'Payment Status: {"Paid" if invoice.is_paid else "Pending"}')

    if settings_obj and settings_obj.receipt_footer:
        p.setFont('Helvetica', 8)
        p.drawString(50, 80, settings_obj.receipt_footer)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_receipt_pdf(deposit, settings_obj=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    company_name = settings_obj.company_name if settings_obj else 'Custody Management'

    p.setFont('Helvetica-Bold', 18)
    p.drawString(50, height - 50, company_name)
    p.setFont('Helvetica-Bold', 14)
    p.drawString(50, height - 80, 'DEPOSIT RECEIPT')

    p.setFont('Helvetica', 11)
    y = height - 110
    line_height = 18

    fields = [
        ('Deposit Number:', deposit.deposit_number),
        ('Visitor Name:', deposit.visitor_name),
        ('Mobile:', deposit.mobile_number),
        ('National ID:', deposit.national_id),
        ('Check-In Date:', deposit.check_in_date.strftime('%Y-%m-%d %H:%M')),
        ('Expected Pickup:', deposit.expected_pickup_date.strftime('%Y-%m-%d') if deposit.expected_pickup_date else 'N/A'),
        ('Description:', deposit.description),
        ('Storage Location:', deposit.get_storage_location_display()),
        ('Shelf:', deposit.shelf_number or 'N/A'),
        ('Status:', deposit.get_status_display()),
    ]

    for label, value in fields:
        p.setFont('Helvetica-Bold', 10)
        p.drawString(50, y, label)
        p.setFont('Helvetica', 10)
        p.drawString(180, y, str(value)[:60])
        y -= line_height

    if deposit.qr_code and os.path.exists(deposit.qr_code.path):
        p.drawImage(deposit.qr_code.path, 450, height - 200, width=80, height=80)

    p.setFont('Helvetica', 8)
    if settings_obj and settings_obj.receipt_footer:
        p.drawString(50, 80, settings_obj.receipt_footer)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_label_pdf(deposit, label_width_mm=50, label_height_mm=30, settings_obj=None):
    buffer = io.BytesIO()
    page_size = (label_width_mm * rl_mm, label_height_mm * rl_mm)
    p = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    p.setFont('Helvetica-Bold', 8)
    p.drawString(2, height - 10, deposit.deposit_number)
    p.setFont('Helvetica', 6)
    p.drawString(2, height - 18, deposit.visitor_name[:20])
    p.drawString(2, height - 25, deposit.description[:25])
    p.drawString(2, height - 32, deposit.check_in_date.strftime('%Y-%m-%d'))

    if deposit.barcode_image and os.path.exists(deposit.barcode_image.path):
        try:
            bw = label_width_mm * 0.6
            bh = label_height_mm * 0.25
            p.drawImage(deposit.barcode_image.path, width - bw - 5, 2, width=bw * rl_mm, height=bh * rl_mm)
        except:
            pass

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def log_activity(user, action, description=None, deposit=None, request=None):
    from .models import ActivityLog
    ip = None
    if request:
        ip = request.META.get('REMOTE_ADDR')
    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        deposit=deposit,
        ip_address=ip,
    )
