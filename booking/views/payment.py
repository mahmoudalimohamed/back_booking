import requests
import json
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from functools import wraps
from decouple import config
from ..models import Booking
from datetime import datetime
from django.utils.timezone import now
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..utils import generate_ticket_pdf, send_ticket_email
logger = logging.getLogger(__name__)

PAYMOB_API_KEY = config('PAY_API_KEY')
PAYMOB_AUTH_URL = config('PAY_AUTH_URL')
PAYMOB_ORDER_URL = config('PAY_ORDER_URL')
PAYMOB_PAYMENT_KEY_URL = config('PAY_PAYMENT_KEY_URL')
PAYMOB_INTEGRATION_ID = config('PAY_INTEGRATION_ID')
PAYMOB_HMAC_SECRET = config('PAY_HMAC_SECRET')
CURRENCY = config('PAY_CURRENCY')
TEMP_LOCK_EXPIRY = 600

def update_booking_status(booking, transaction_success, transaction_id=None):
    booking.payment_status = "PAID" if transaction_success else "FAILED"
    booking.status = "CONFIRMED" if transaction_success else "CANCELLED"
    if transaction_id:
        booking.payment_reference = transaction_id
    booking.payment_date = now()
    booking.save()

def handle_exceptions(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except Booking.DoesNotExist:
            return JsonResponse({"error": "Booking not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {e}"}, status=500)
    return wrapper

class PaymentHelper:
    @staticmethod
    def get_auth_token():
        token = cache.get("paymob_auth_token")
        if token:
            return token
        try:
            res = requests.post(PAYMOB_AUTH_URL, json={"api_key": PAYMOB_API_KEY})
            res.raise_for_status()
            token = res.json().get("token")
            cache.set("paymob_auth_token", token, timeout=3600)
            return token
        except requests.RequestException as e:
            print(f"Auth token error: {e}")
            return None

    @staticmethod
    def create_order_data(trip, seats, token):
        total = trip.price * len(seats) * 100
        item_name = f"Trip from {trip.start_location.city.name} to {trip.destination.city.name}"
        return {
            "auth_token": token,
            "delivery_needed": False,
            "amount_cents": str(total),
            "currency": CURRENCY,
            "items": [{
                "name": item_name,
                "amount_cents": str(trip.price * 100),
                "quantity": len(seats),
                "description": f"Seats: {', '.join(map(str, seats))}",
            }]
        }

    @staticmethod
    def create_payment_key_data(token, order_id, amount, user):
        name = getattr(user, "name", "User Customer").split(maxsplit=1)
        first = name[0]
        last = name[1] if len(name) > 1 else "Customer"
        phone = getattr(user, "phone_number", "+201234567890")
        email = getattr(user, "email", "user@example.com")
        return {
            "auth_token": token,
            "amount_cents": str(amount),
            "expiration": 3600,
            "order_id": order_id,
            "currency": CURRENCY,
            "integration_id": PAYMOB_INTEGRATION_ID,
            "billing_data": {
                "first_name": first,
                "last_name": last,
                "phone_number": phone,
                "email": email,
                "city": "Cairo",
                "country": "EG",
                "street": "123 Street",
                "building": "10",
                "floor": "2",
                "apartment": "5A",
                "postal_code": "12345",
                "state": "Cairo",
            },
            "lock_order_when_paid": True
        }

@csrf_exempt
@handle_exceptions
def get_payment_key(request, order_id):
    token = PaymentHelper.get_auth_token()
    if not token:
        return JsonResponse({"error": "Auth failed"}, status=500)
    order_res = requests.get(f"{PAYMOB_ORDER_URL}/{order_id}", headers={"Authorization": f"Bearer {token}"})
    if order_res.status_code != 200:
        return JsonResponse({"error": "Invalid order_id"}, status=400)
    amount = order_res.json().get("amount_cents")
    booking = Booking.objects.get(payment_order_id=order_id)
    user = booking.user
    key_data = PaymentHelper.create_payment_key_data(token, order_id, amount, user)
    res = requests.post(PAYMOB_PAYMENT_KEY_URL, json=key_data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    res.raise_for_status()
    payment_key = res.json().get("token")
    if not payment_key:
        return JsonResponse({"error": "No payment key"}, status=500)
    return JsonResponse({"payment_key": payment_key}, status=200)

@csrf_exempt
@handle_exceptions
def paymob_processed_callback(request):
    params = dict(request.GET.items()) if request.method == "GET" else json.loads(request.body.decode())
    if isinstance(params, dict) and 'obj' in params:
        params = params['obj']
    order_id = params.get("order")
    transaction_success = str(params.get("success")).lower() == "true"
    transaction_id = params.get("id")
    booking = Booking.objects.get(payment_order_id=order_id)
    update_booking_status(booking, transaction_success, transaction_id)
    return JsonResponse({
        "message": "Booking updated",
        "status": booking.payment_status,
        "transaction_id": transaction_id,
    }, status=200)

@csrf_exempt
@handle_exceptions
def paymob_response_callback(request):
    params = dict(request.GET.items()) if request.method == "GET" else json.loads(request.body.decode())
    order_id = params.get("order")
    transaction_success = str(params.get("success")).lower() == "true"
    booking = Booking.objects.get(payment_order_id=order_id)
    update_booking_status(booking, transaction_success, params.get("id"))
    if transaction_success:
        pdf_path = f'tickets/ticket-{booking.id}.pdf'
        default_storage.save(pdf_path, ContentFile(b''))
        generate_ticket_pdf(booking, default_storage.path(pdf_path))
        send_ticket_email(booking, default_storage.path(pdf_path))
        default_storage.delete(pdf_path)
    frontend_url = "https://busbooking-virid.vercel.app/booking-success"
    redirect_url = f"{frontend_url}?order_id={booking.id}&success={transaction_success}"
    return redirect(redirect_url)