from rest_framework import serializers, viewsets
from .models import User, Trip, Booking, City, Area
from django.db import transaction
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number', 'user_type', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_phone_number(self, value):
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError("Phone number must be exactly 11 digits.")
        return value

    def create(self, validated_data):
        user = User(**validated_data)
        # Set username to email or something unique
        user.username = validated_data['email']  # 🔥 This line solves your issue
        user.set_password(validated_data['password'])
        user.save()
        return user



class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name']


class AreaSerializer(serializers.ModelSerializer):
    city = serializers.StringRelatedField(read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(source='city', queryset=City.objects.all(), write_only=True)

    class Meta:
        model = Area
        fields = ['id', 'name', 'city', 'city_id']


class TripSerializer(serializers.ModelSerializer):
    start_location = serializers.StringRelatedField()
    destination = serializers.StringRelatedField()
    formatted_departure = serializers.SerializerMethodField()
    formatted_arrival = serializers.SerializerMethodField()
    seat_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id', 'start_location', 'destination','bus_type', 'departure_date', 'arrival_date',
            'total_seats', 'available_seats', 'price', 'created_at', 'updated_at',
            'formatted_departure', 'formatted_arrival', 'seat_statuses'
        ]
        read_only_fields = ['id', 'available_seats', 'created_at', 'updated_at']

    def get_formatted_departure(self, obj):
        return obj.departure_date.strftime('%Y-%m-%d')

    def get_formatted_arrival(self, obj):
        return obj.arrival_date.strftime('%Y-%m-%d')

    def get_seat_statuses(self, obj):
        return [{"seat": seat, "status": status} for seat, status in obj.seats.items()]


class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    trip = TripSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'trip', 'seats_booked', 'selected_seats', 'status', 
            'customer_name', 'customer_phone', 'booking_date', 'total_price', 
            'payment_status', 'payment_reference', 'expires_at', 'payment_type'
        ]
        read_only_fields = ['id', 'user', 'booking_date', 'total_price', 
                          'payment_status', 'expires_at', 'payment_type']

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user.user_type == 'Admin':
            if not data.get('customer_name') or not data.get('customer_phone'):
                raise serializers.ValidationError(
                    "Customer name and phone are required for admin bookings"
                )
        return data

    def create(self, validated_data):
        trip = self.context.get('trip')
        request = self.context.get('request')
        
        if not trip:
            raise serializers.ValidationError("Trip is required in context.")

        with transaction.atomic():
            booking = Booking(
                user=request.user,
                trip=trip,
                seats_booked=validated_data['seats_booked'],
                selected_seats=validated_data['selected_seats'],
                status='PENDING',
                expires_at=timezone.now() + timezone.timedelta(minutes=5),
                customer_name=validated_data.get('customer_name', request.user.name),
                customer_phone=validated_data.get('customer_phone', request.user.phone_number),
                payment_type=validated_data.get('payment_type', 'ONLINE')
            )
            booking.save()
        return booking
    
    
# serializers for lightweight data transfer
class LightweightAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['name']  # Only include the name to reduce data


class LightweightTripSerializer(serializers.ModelSerializer):
    start_location = LightweightAreaSerializer()
    destination = LightweightAreaSerializer()

    class Meta:
        model = Trip
        fields = ['id', 'start_location', 'destination', 'bus_type', 'departure_date', 'price']  # Reduced fields


class LightweightBookingSerializer(serializers.ModelSerializer):
    trip = LightweightTripSerializer()

    class Meta:
        model = Booking
        fields = ['id', 'trip', 'seats_booked', 'selected_seats', 'payment_status', 'status', 'booking_date', 'total_price','payment_type']  # Reduced fields


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related(
        'user', 'trip', 'trip__start_location', 'trip__destination'
    ).only(
        'id', 'user__id', 'trip__id', 'trip__start_location__name', 'trip__destination__name',
        'seats_booked', 'selected_seats', 'status', 'customer_name', 'customer_phone',
        'booking_date', 'total_price', 'payment_status', 'expires_at', 'payment_type'
    )
    serializer_class = BookingSerializer


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.select_related(
        'start_location', 'destination'
    ).only(
        'id', 'start_location__name', 'destination__name', 'bus_type', 'departure_date',
        'arrival_date', 'total_seats', 'available_seats', 'price', 'created_at', 'updated_at'
    )
    serializer_class = TripSerializer


class LightweightBookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related(
        'trip__start_location', 'trip__destination'
    ).only(
        'id', 'trip__id', 'trip__start_location__name', 'trip__destination__name',
        'seats_booked', 'selected_seats', 'payment_status', 'status', 'booking_date',
        'total_price', 'payment_type'
    )
    serializer_class = LightweightBookingSerializer