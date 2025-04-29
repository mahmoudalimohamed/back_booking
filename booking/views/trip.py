from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from ..models import City, Trip
from ..serializers import TripSerializer
from django.db.models.functions import TruncDate
from datetime import datetime

# Location List View
class LocationListView(generics.ListAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        cities = City.objects.prefetch_related('areas').all()
        data = [
            {'id': city.id, 'name': city.name, 'areas': [ { 'id': area.id, 'name': area.name } for area in city.areas.all() ]}
            for city in cities
        ]
        return Response({'cities': data}, status=status.HTTP_200_OK)

# Trip Search View
class TripSearchView(generics.ListAPIView):
    serializer_class = TripSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        start_city = self.request.query_params.get('start_city', '')
        start_area = self.request.query_params.get('start_area', '')
        destination_city = self.request.query_params.get('destination_city', '')
        destination_area = self.request.query_params.get('destination_area', '')
        departure_date = self.request.query_params.get('departure_date', None)

        queryset = Trip.objects.filter(available_seats__gt=0)

        if start_city:
            if start_city.isdigit():
                queryset = queryset.filter(start_location__city_id=start_city)
            else:
                queryset = queryset.filter(start_location__city__name__icontains=start_city)
        if start_area:
            if start_area.isdigit():
                queryset = queryset.filter(start_location_id=start_area)
            else:
                queryset = queryset.filter(start_location__name__icontains=start_area)

        if destination_city:
            if destination_city.isdigit():
                queryset = queryset.filter(destination__city_id=destination_city)
            else:
                queryset = queryset.filter(destination__city__name__icontains=destination_city)
        if destination_area:
            if destination_area.isdigit():
                queryset = queryset.filter(destination_id=destination_area)
            else:
                queryset = queryset.filter(destination__name__icontains=destination_area)

        if departure_date:
            try:
                date_obj = datetime.strptime(departure_date, '%Y-%m-%d').date()
                queryset = queryset.annotate(date_only=TruncDate('departure_date')).filter(date_only=date_obj)
            except ValueError:
                queryset = queryset.none()

        return queryset