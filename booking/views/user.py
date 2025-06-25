from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from ..models import User, Booking
from ..serializers import UserSerializer, LightweightBookingSerializer
from django.core.mail import send_mail
from django.utils.timezone import now
from rest_framework_simplejwt.tokens import RefreshToken

# User Registration View
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(
                {'message': 'Registration successful', 'user': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save()

# User Login View
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'message': 'Login successful',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }, status=status.HTTP_200_OK)

            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# User Logout View
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Request Password Reset
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        platform = request.data.get('platform','wed')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            if platform == 'mobile':
                reset_link = f"bookingappmaher://reset-password/{uid}/{token}"
                
            else:
                reset_link = f"https://busbooking-virid.vercel.app/reset-password?uid={uid}&token={token}"

            html_message = render_to_string('email/password_reset.html', {
                'user': user,
                'reset_link': reset_link,
                'valid_hours': 24
            })

            plain_message = strip_tags(html_message)

            send_mail(
                subject='Reset Your Password',
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            return Response({'message': 'Password reset link sent to your email'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'Password reset link sent to your email'}, status=status.HTTP_200_OK)

# Reset Password
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')

        if not uid or not token or not password:
            return Response({
                'error': 'UID, token and new password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)

            if not default_token_generator.check_token(user, token):
                return Response({
                    'error': 'Token is invalid or expired'
                }, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(password)
            user.save()

            return Response({
                'message': 'Password reset successfully'
            }, status=status.HTTP_200_OK)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid reset link'
            }, status=status.HTTP_400_BAD_REQUEST)

# User Profile View
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_serializer = UserSerializer(user)

        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 5))
        offset = (page - 1) * limit

        bookings = Booking.objects.filter(user=user).select_related(
            'trip__start_location__city',
            'trip__destination__city'
        ).order_by('-booking_date')[offset:offset + limit]

        bookings_serializer = LightweightBookingSerializer(bookings, many=True)

        total_bookings = Booking.objects.filter(user=user).count()

        profile_data = {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'phone_number': user.phone_number,
                'user_type': user.user_type
            },
            'bookings': bookings_serializer.data,
            'pagination': {
                'total': total_bookings,
                'page': page,
                'limit': limit,
                'total_pages': (total_bookings + limit - 1) // limit
            }
        }

        return Response(profile_data, status=status.HTTP_200_OK)