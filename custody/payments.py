import uuid
import json
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.core.signing import TimestampSigner
from .models import Deposit, PaymentTransaction, StorageBox
from .utils import encrypt_reference, generate_qr_encrypted, generate_qr_code_image, generate_barcode_image, log_activity

signer = TimestampSigner()

def calculate_price(item_type, duration_days):
    """Backend-only price calculation from admin-defined PricingRules."""
    from .models import PricingRule
    rule = PricingRule.objects.filter(
        item_type=item_type, duration_days=duration_days, is_active=True
    ).first()
    if rule:
        return rule.price
    fallback = PricingRule.objects.filter(item_type=item_type, is_active=True).order_by('duration_days').first()
    if fallback:
        return fallback.price * duration_days
    return Decimal('50.00')

def create_checkout_session(booking):
    """Create a payment session and generate a one-time payment token."""
    token = signer.sign(f"{booking.deposit_number}:{uuid.uuid4().hex}")
    booking.payment_token = token
    booking.save(update_fields=['payment_token'])
    return token

def verify_payment_token(token, booking_number):
    """Verify a one-time payment token."""
    from django.core.signing import BadSignature, SignatureExpired
    try:
        raw = signer.unsign(token, max_age=3600)
        ref, _ = raw.split(':', 1)
        return ref == booking_number
    except (BadSignature, SignatureExpired, ValueError):
        return False

@transaction.atomic
def process_successful_payment(booking_number, gateway_txn_id=None, gateway='mock', gateway_response=None):
    """Process webhook-confirmed payment: assign locker, generate QR, update status."""
    booking = Deposit.objects.select_related('storage_box').filter(deposit_number=booking_number).first()
    if not booking:
        return None
    if booking.status == 'paid':
        return booking
    booking.status = 'paid'
    booking.payment_status = 'paid'
    txn, _ = PaymentTransaction.objects.get_or_create(
        booking=booking,
        transaction_id=gateway_txn_id or f"MOCK-{uuid.uuid4().hex[:12].upper()}",
        defaults={'amount': booking.total_amount, 'gateway': gateway, 'gateway_response': gateway_response, 'status': 'completed', 'processed_at': timezone.now()}
    )
    if not txn.status == 'completed':
        txn.status = 'completed'
        txn.processed_at = timezone.now()
        txn.save()
    available_box = StorageBox.objects.filter(
        is_available=True, item_type=booking.item_type
    ).first()
    if not available_box:
        available_box = StorageBox.objects.filter(is_available=True).first()
    if available_box and not booking.storage_box:
        booking.storage_box = available_box
        available_box.is_available = False
        available_box.save()
    encrypted_ref = encrypt_reference(booking.deposit_number)
    booking.encrypted_reference = encrypted_ref
    qr_file, _ = generate_qr_encrypted(booking.deposit_number)
    if qr_file:
        booking.qr_code.save(f'qr_{booking.deposit_number}.png', qr_file)
    barcode_img = generate_barcode_image(booking.deposit_number)
    if barcode_img:
        booking.barcode_image.save(f'barcode_{booking.deposit_number}.png', barcode_img)
    booking.save()
    log_activity(None, 'Payment completed via webhook', f'Booking {booking.deposit_number} paid, locker {booking.storage_box.box_number if booking.storage_box else "auto"} assigned', booking)
    return booking
