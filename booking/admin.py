from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Trip, Booking, City, Area
from django.db import transaction
from django.utils.timezone import timedelta
from django.contrib import messages


# Admin for User model
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('name', 'email', 'phone_number', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser')
    search_fields = ('name', 'email', 'phone_number')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'phone_number', 'user_type')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'email', 'phone_number', 'user_type', 'password1', 'password2'),
        }),
    )

    ordering = ('email',)


# Admin for City model
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)


# Admin for Area model
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'created_at', 'updated_at')
    list_filter = ('city',)
    search_fields = ('name', 'city__name')
    ordering = ('city', 'name')


# Admin for Trip model
@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('start_location', 'destination', 'bus_type',
                    'departure_date', 'arrival_date', 
                    'total_seats', 'available_seats',
                    'price', 'display_seats')
    list_filter = ('start_location', 'destination', 'departure_date', 'bus_type')
    search_fields = ('start_location__name', 'destination__name', 'bus_type')

    fieldsets = (
        (None, {'fields': ('start_location', 'destination','bus_type')}),
        ('Schedule', {'fields': ('departure_date', 'arrival_date')}),
        ('Details', {'fields': ('total_seats', 'available_seats', 'price', 'seats')}),
    )

    readonly_fields = ('available_seats', 'created_at', 'updated_at', 'seats')

    actions = ['duplicate_trip_for_30_days']

    def display_seats(self, obj):
        """Display the seat availability in a readable format."""
        return ", ".join([f"{seat}: {status}" for seat, status in obj.seats.items()])

    display_seats.short_description = "Seats"

    def duplicate_trip_for_30_days(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one trip to duplicate.", level=messages.ERROR)
            return

        original_trip = queryset.first()

        for i in range(1, 30):  # Next 29 days
            new_departure = original_trip.departure_date + timedelta(days=i)
            new_arrival = original_trip.arrival_date + timedelta(days=i)

            Trip.objects.create(
                bus_type=original_trip.bus_type,
                start_location=original_trip.start_location,
                destination=original_trip.destination,
                departure_date=new_departure,
                arrival_date=new_arrival,
                total_seats=original_trip.total_seats,
                available_seats=original_trip.total_seats,
                seats={str(n): "available" for n in range(1, original_trip.total_seats + 1)},
                price=original_trip.price,
            )

        self.message_user(request, "Trip duplicated for 30 consecutive days successfully.")

    duplicate_trip_for_30_days.short_description = "Duplicate selected Trip for 30 days"


# Admin for Booking model (Updated)
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'customer_name', 'customer_phone', 'trip', 'seats_booked', 'display_selected_seats', 'status', 'booking_date', 'total_price',
                    "payment_reference", "payment_status", "expires_at","payment_type",)
    list_filter = ('status', 'booking_date')
    search_fields = ('user__name', 'trip__start_location__name', 'trip__destination__name')

    fieldsets = (
        (None, {'fields': ('user', 'trip')}),
        ('Booking Details', {'fields': ('seats_booked', 'selected_seats', 'status', 'total_price')}),
    )

    readonly_fields = ('total_price', 'booking_date')

    def display_selected_seats(self, obj):
        """Display booked seat numbers in admin panel."""
        return ", ".join(map(str, obj.selected_seats))

    display_selected_seats.short_description = "Selected Seats"

    actions = ['confirm_bookings']

    def confirm_bookings(self, request, queryset):
        queryset.update(status='CONFIRMED')
        self.message_user(request, "Selected bookings have been confirmed.")
    confirm_bookings.short_description = "Confirm selected bookings"

    def delete_model(self, request, obj):
        """Override delete to update trip seats."""
        with transaction.atomic():
            trip = obj.trip
            for seat_number in obj.selected_seats:
                trip.seats[str(seat_number)] = 'available'
            trip.available_seats += obj.seats_booked
            trip.save()
            super().delete_model(request, obj)