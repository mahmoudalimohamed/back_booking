from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone 


PHONE_REGEX = RegexValidator(regex=r'^\d{11}$', message="Phone number must be exactly 11 digits.")

# Custom User model extending Django's AbstractUser
class User(AbstractUser):
    name = models.CharField(max_length=50, blank=False, null=False , default='Anonymous')
    email = models.EmailField(unique=True, blank=False, null=False)
    phone_number = models.CharField(validators=[PHONE_REGEX], max_length=11, unique=True, blank=False, null=False)
    user_type = models.CharField(max_length=20, choices=[('Passenger', 'Passenger'), ('Admin', 'Admin')], default='Passenger')

    # Custom validation method to enforce additional rules
    def clean(self):
        super().clean()  # Call parent class's clean method

    # Override save method to ensure validation runs before saving
    def save(self, *args, **kwargs):
        self.clean()  # Run validation
        super().save(*args, **kwargs)  # Call parent save method

    # String representation of the User object for easy identification
    def __str__(self):
        return f'name: {self.name} - phone: {self.phone_number} '


#Model for City
class City(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def __str__(self):
        return self.name


#Model for Area
class Area(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='areas')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Areas'
        ordering = ['name']
        unique_together = ['city', 'name']

    def __str__(self):
        return f'{self.city.name}, {self.name}'


# Model for a trip, representing a journey between locations
class Trip(models.Model):
    Bus_TYBE_CHOICES = [('STANDARD','Standard'),('DELUXE','Deluxe'),('VIP','Vip'),('MINI','Mini'),]
    bus_type = models.CharField(max_length=20, choices=Bus_TYBE_CHOICES,default='Standard')
    start_location = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='start_trips')
    destination = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='destination_trips')
    departure_date = models.DateTimeField(default=timezone.now)
    arrival_date = models.DateTimeField(default=timezone.now)

    total_seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField(blank=True, null=True)
    seats = models.JSONField(default=dict) 

    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.start_location == self.destination:
            raise ValidationError("Start and destination can't be the same.")
        if self.available_seats is None:
            self.available_seats = self.total_seats
        elif self.available_seats > self.total_seats:
            raise ValidationError("Available seats can't exceed total seats.")
        
        if not self.seats:
            self.seats = {str(i): 'available' for i in range(1, self.total_seats + 1)}

    def save(self, *args, **kwargs):
        self.full_clean()  # Automatically calls `clean()`
        super().save(*args, **kwargs)

    def is_seat_available(self, seat_number):
        return self.seats.get(str(seat_number)) == 'available'

    def __str__(self):
        return f"{self.start_location} → {self.destination} ({self.bus_type}) on {self.departure_date:%Y-%m-%d %H:%M}"

    class Meta:
        indexes = [
            models.Index(fields=['start_location', 'destination', 'departure_date']),  # Composite index for trip search
        ]



# Model for a booking, representing a reservation made by a user for a specific trip
class Booking(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed'), ('CANCELLED', 'Cancelled')]
    PAYMENT_CHOICES = [('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed')]
    PAYMENT_TYPE_CHOICES = [('CASH', 'Cash'), ('ONLINE', 'Online'), ('E Wallet', 'e wallet')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    customer_name = models.CharField(max_length=50, default='Anonymous')
    customer_phone = models.CharField(max_length=11, validators=[PHONE_REGEX], default='00000000000')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings')

    seats_booked = models.PositiveIntegerField()
    selected_seats = models.JSONField(default=list)

    payment_status = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='PENDING')
    payment_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='ONLINE')
    booking_date = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)


    class Meta:
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['status', 'expires_at']),  # Existing index
            models.Index(fields=['trip', 'user']),  # Composite index for trip and user
            models.Index(fields=['payment_status', 'payment_type']),  # Composite index for payment fields
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            with transaction.atomic():
                trip = Trip.objects.select_for_update().get(pk=self.trip.pk)
                self._book_seats(trip)
                self.total_price = trip.price * self.seats_booked
                self.expires_at = timezone.now() + timezone.timedelta(minutes=2)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _book_seats(self, trip):
        selected = set(map(str, self.selected_seats))
        if len(selected) != self.seats_booked:
            raise ValidationError("Number of selected seats must match seats booked.")
        
        if trip.available_seats < self.seats_booked:
            raise ValidationError("Not enough available seats.")
        
        for seat in selected:
            if trip.seats.get(seat) != 'available':
                raise ValidationError(f"Seat {seat} is not available.")
            trip.seats[seat] = 'booked'

        trip.available_seats -= self.seats_booked
        trip.save()

    def cancel(self):
        if self.status != 'CANCELLED':
            with transaction.atomic():
                trip = Trip.objects.select_for_update().get(pk=self.trip.pk)
                for seat in map(str, self.selected_seats):
                    trip.seats[seat] = 'available'
                trip.available_seats += self.seats_booked
                trip.save()
                self.status = 'CANCELLED'
                self.save()

    def __str__(self):
        return f"{self.user.username} booking: {self.trip}"




