from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files.base import ContentFile
from rest_framework.response import Response
from ..serializers import BookingSerializer
from rest_framework.views import APIView
from datetime import datetime, timedelta
from rest_framework import serializers
from django.http import JsonResponse
from django.core.cache import cache
from ..models import Booking, Trip
from django.db import transaction
import uuid
import logging
import requests
from decouple import config
from .payment import PaymentHelper
from ..utils import generate_ticket_pdf, send_ticket_email

# Define PAYMOB_ORDER_URL
PAYMOB_ORDER_URL = config('PAY_ORDER_URL')
logger = logging.getLogger(__name__)
TEMP_LOCK_EXPIRY = 600

class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        cache_key = f"trip_seats_{trip_id}"
        seats = cache.get(cache_key)
        if not seats:
            trip = get_object_or_404(
                Trip.objects.select_related('start_location', 'destination').only(
                    'id', 'total_seats', 'available_seats', 'seats',
                    'start_location__name', 'destination__name', 'bus_type', 'departure_date', 'price'
                ),
                id=trip_id
            )
            seats = {
                'total_seats': trip.total_seats,
                'available_seats': trip.available_seats,
                'seat_status': trip.seats,
                'unavailable_seats': [
                    seat_num for seat_num, status in trip.seats.items()
                    if status != 'available'
                ]
            }
            cache.set(cache_key, seats, timeout=300)  # Cache for 5 minutes
        return Response(seats, status=200)

    def post(self, request, trip_id):
        trip = get_object_or_404(
            Trip.objects.select_related('start_location', 'destination').only(
                'id', 'total_seats', 'available_seats', 'seats', 'price',
                'start_location__name', 'destination__name', 'bus_type', 'departure_date'
            ),
            id=trip_id
        )
        seats = request.data.get("selected_seats", [])
        payment_type = request.data.get("payment_type", "ONLINE").upper()
        
        if request.user.user_type == 'Passenger':
            customer_name = request.user.name
            customer_phone = request.user.phone_number
        else:  # Admin
            customer_name = request.data.get('customer_name')
            customer_phone = request.data.get('customer_phone')
            if not customer_name or not customer_phone:
                return Response({"error": "Customer name and phone are required for admin bookings"}, status=400)

        data = {
            "selected_seats": seats,
            "seats_booked": len(seats),
            "payment_type": payment_type,
            "customer_name": customer_name,
            "customer_phone": customer_phone
        }
        serializer = BookingSerializer(data=data, context={'trip': trip, 'request': request})

        try:
            serializer.is_valid(raise_exception=True)
            temp_booking_ref = str(uuid.uuid4())
            cache_key = f"temp_booking_{trip.id}_{temp_booking_ref}"
            cache.set(cache_key, {
                'seats': seats,
                'user_id': request.user.id,
                'payment_type': payment_type,
                'customer_name': customer_name,
                'customer_phone': customer_phone
            }, timeout=TEMP_LOCK_EXPIRY)

            return Response({
                "message": "Booking initiated",
                "temp_booking_ref": temp_booking_ref,
                "expires_at": (timezone.now() + timedelta(seconds=TEMP_LOCK_EXPIRY)).isoformat()
            }, status=200)
        except serializers.ValidationError as e:
            return Response({"error": str(e)}, status=400)

class ConfirmBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id, temp_booking_ref):
        trip = get_object_or_404(
            Trip.objects.select_related('start_location', 'destination').only(
                'id', 'total_seats', 'available_seats', 'seats', 'price',
                'start_location__name', 'destination__name', 'bus_type', 'departure_date'
            ),
            id=trip_id
        )
        cache_key = f"temp_booking_{trip.id}_{temp_booking_ref}"
        temp_booking = cache.get(cache_key)
        
        if not temp_booking:
            return Response({"error": "Temporary booking expired or not found"}, status=404)
        if temp_booking['user_id'] != request.user.id:
            return Response({"error": "Unauthorized"}, status=403)

        seats = temp_booking['seats']
        payment_type = temp_booking['payment_type']
        customer_name = request.data.get('customer_name', temp_booking.get('customer_name'))
        customer_phone = request.data.get('customer_phone', temp_booking.get('customer_phone'))

        data = {
            "selected_seats": seats,
            "seats_booked": len(seats),
            "payment_type": payment_type,
            "customer_name": customer_name,
            "customer_phone": customer_phone
        }
        serializer = BookingSerializer(data=data, context={'trip': trip, 'request': request})

        try:
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                booking = serializer.save()
            cache.delete(cache_key)

            if payment_type == "ONLINE":
                token = PaymentHelper.get_auth_token()
                if not token:
                    booking.delete()
                    return Response({"error": "Payment auth failed"}, status=500)
                order_data = PaymentHelper.create_order_data(trip, seats, token)
                order_res = requests.post(PAYMOB_ORDER_URL, json=order_data, headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }, timeout=10)
                order_res.raise_for_status()
                order_id = order_res.json().get("id")
                if not order_id:
                    booking.delete()
                    return Response({"error": "No order ID"}, status=500)
                booking.payment_order_id = order_id
                booking.save(update_fields=["payment_order_id"])
                return Response({
                    "message": "Booking confirmed",
                    "booking": {
                        "id": booking.id,
                        "seats_booked": booking.seats_booked,
                        "selected_seats": booking.selected_seats,
                        "payment_status": booking.payment_status,
                        "status": booking.status,
                        "total_price": str(booking.total_price),
                        "payment_type": booking.payment_type
                    },
                    "order_id": order_id
                }, status=201)
            else:
                booking.status = 'CONFIRMED'
                booking.payment_status = 'PAID'
                booking.payment_type = 'CASH'
                booking.save(update_fields=['status', 'payment_status', 'payment_type'])
                pdf_path = f'tickets/ticket-{booking.id}.pdf'
                default_storage.save(pdf_path, ContentFile(b''))
                generate_ticket_pdf(booking, default_storage.path(pdf_path))
                send_ticket_email(booking, default_storage.path(pdf_path))
                default_storage.delete(pdf_path)
                frontend_url = "https://busbooking-virid.vercel.app/booking-success"
                redirect_url = f"{frontend_url}?order_id={booking.id}&success=true"
                return Response({
                    "message": "Booking confirmed with cash payment",
                    "booking": {
                        "id": booking.id,
                        "seats_booked": booking.seats_booked,
                        "selected_seats": booking.selected_seats,
                        "payment_status": booking.payment_status,
                        "status": booking.status,
                        "total_price": str(booking.total_price),
                        "payment_type": booking.payment_type
                    },
                    "redirect_url": redirect_url
                }, status=201)
        except (serializers.ValidationError, requests.RequestException) as e:
            if 'booking' in locals():
                booking.delete()
            return Response({"error": str(e)}, status=500)

# Other views unchanged (BookingCancelView, BookingDetailView, run_scheduled_job)
class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        if request.user.user_type != 'Admin':
            return Response({"error": "Only admins can cancel bookings"}, status=403)
        if booking.status == 'CANCELLED':
            return Response({"error": "Booking is already cancelled"}, status=400)
        booking.cancel()
        return Response({"message": "Booking cancelled successfully"}, status=200)

class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            if str(order_id).isdigit():
                booking = Booking.objects.get(id=order_id)
            else:
                booking = Booking.objects.get(payment_order_id=order_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)
        if booking.user != request.user and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=403)
        serializer = BookingSerializer(booking)
        return Response({"booking": serializer.data}, status=200)

@csrf_exempt
def run_scheduled_job(request):
    current_time = timezone.now()
    expired_bookings = Booking.objects.filter(status='PENDING', expires_at__lt=current_time)
    count = expired_bookings.count()
    for booking in expired_bookings:
        booking.cancel()
    print(f"Cancelled {count} expired bookings.")
    return JsonResponse({"status": "OK", "cancelled": count})