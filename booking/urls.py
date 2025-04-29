#booking/urls.py
from django.urls import path
from .views.user import (RegisterView, LoginView, LogoutView, UserProfileView, PasswordResetRequestView, PasswordResetConfirmView)
from .views.trip import LocationListView, TripSearchView
from .views.booking import ( BookingDetailView, BookingCancelView , BookingCreateView, ConfirmBookingView, run_scheduled_job)
from .views.payment import (get_payment_key, paymob_response_callback, paymob_processed_callback)

app_name = 'bus_booking'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Location List
    path('locations/', LocationListView.as_view(), name='location_list'),

    # Trip Search
    path('trips/search/', TripSearchView.as_view(), name='trip_search'),

    # Booking
    path('trips/<int:trip_id>/book/', BookingCreateView.as_view(), name='book_trip'),
    
    path('trips/<int:trip_id>/confirm/<str:temp_booking_ref>/', ConfirmBookingView.as_view(), name='confirm_booking'),

    # Payment
    path('get_payment_key/<int:order_id>/', get_payment_key, name='payment_key'),

    path('paymob/processed_callback/', paymob_processed_callback, name='paymob_processed_callback'),

    path('paymob/response_callback/', paymob_response_callback, name='paymob_response_callback'),

    # Booking Detail
    path('bookings/detail/<int:order_id>/', BookingDetailView.as_view(), name='booking_detail'),

    # Booking Cancellation
    path('bookings/<int:booking_id>/cancel/', BookingCancelView.as_view(), name='cancel_booking'),

    # User Profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),

    path("run-job/", run_scheduled_job, name="run_job"),

    path('password_reset/', PasswordResetRequestView.as_view(), name='password_reset'),

    path('password_reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]