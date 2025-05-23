# Generated by Django 5.0.2 on 2025-04-29 23:11

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Cities',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('name', models.CharField(default='Anonymous', max_length=50)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone_number', models.CharField(max_length=11, unique=True, validators=[django.core.validators.RegexValidator(message='Phone number must be exactly 11 digits.', regex='^\\d{11}$')])),
                ('user_type', models.CharField(choices=[('Passenger', 'Passenger'), ('Admin', 'Admin')], default='Passenger', max_length=20)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='areas', to='booking.city')),
            ],
            options={
                'verbose_name_plural': 'Areas',
                'ordering': ['name'],
                'unique_together': {('city', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bus_type', models.CharField(choices=[('STANDARD', 'Standard'), ('DELUXE', 'Deluxe'), ('VIP', 'Vip'), ('MINI', 'Mini')], default='Standard', max_length=20)),
                ('departure_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('arrival_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('total_seats', models.PositiveIntegerField()),
                ('available_seats', models.PositiveIntegerField(blank=True, null=True)),
                ('seats', models.JSONField(default=dict)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('destination', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='destination_trips', to='booking.area')),
                ('start_location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='start_trips', to='booking.area')),
            ],
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(default='Anonymous', max_length=50)),
                ('customer_phone', models.CharField(default='00000000000', max_length=11, validators=[django.core.validators.RegexValidator(message='Phone number must be exactly 11 digits.', regex='^\\d{11}$')])),
                ('seats_booked', models.PositiveIntegerField()),
                ('selected_seats', models.JSONField(default=list)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed')], default='PENDING', max_length=10)),
                ('payment_order_id', models.CharField(blank=True, db_index=True, max_length=100, null=True, unique=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=10)),
                ('payment_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('payment_type', models.CharField(choices=[('CASH', 'Cash'), ('ONLINE', 'Online'), ('E Wallet', 'e wallet')], default='ONLINE', max_length=10)),
                ('booking_date', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='booking.trip')),
            ],
            options={
                'ordering': ['-booking_date'],
            },
        ),
        migrations.AddIndex(
            model_name='trip',
            index=models.Index(fields=['start_location', 'destination', 'departure_date'], name='booking_tri_start_l_180699_idx'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['status', 'expires_at'], name='booking_boo_status_9e1025_idx'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['trip', 'user'], name='booking_boo_trip_id_5c9c04_idx'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['payment_status', 'payment_type'], name='booking_boo_payment_2b5e63_idx'),
        ),
    ]
