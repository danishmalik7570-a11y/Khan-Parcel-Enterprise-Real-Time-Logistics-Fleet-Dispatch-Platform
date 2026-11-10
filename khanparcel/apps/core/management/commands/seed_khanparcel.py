# =============================================================================
# Khan Parcel — Seed Data Command
# =============================================================================

from __future__ import annotations

import random
from decimal import Decimal
from typing import Any

from apps.core.gis_compat import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.orders.models import Order, OrderStatus, PaymentMethod, PaymentStatus
from apps.pricing.models import PriceRule, PromoCode, Quote
from apps.pricing.services import QuoteService
from apps.riders.models import (
    DocumentStatus,
    DocumentType,
    ReviewStatus,
    RiderDocument,
    RiderProfile,
    RiderStatus,
    Vehicle,
    VehicleType,
)

ISLAMABAD_COORDS = [
    (33.7297, 73.0746, "Sector F-6 Markaz, Islamabad"),
    (33.7214, 73.0564, "Sector F-7 Jinnah Super, Islamabad"),
    (33.7100, 73.0360, "Sector F-8 Markaz, Islamabad"),
    (33.7088, 73.0552, "Blue Area, Jinnah Avenue, Islamabad"),
    (33.6920, 73.0280, "Sector G-9 Karachi Company, Islamabad"),
    (33.6732, 73.0784, "Sector I-8 Markaz, Islamabad"),
    (33.6688, 72.9982, "Sector G-11 Markaz, Islamabad"),
    (33.6425, 72.9930, "Sector H-12 NUST, Islamabad"),
    (33.5971, 73.0538, "Saddar Bazaar, Rawalpindi"),
    (33.5412, 73.1118, "Bahria Town Phase 4, Rawalpindi"),
]


class Command(BaseCommand):
    help = "Seed database with initial Price Rules, Admin, Dispatchers, Riders, and Orders"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Seeding Khan Parcel database...")

        # 1. Staff Admin User
        admin, _ = User.objects.get_or_create(
            phone="+923000000001",
            defaults={
                "name": "Super Admin",
                "email": "admin@khanparcel.com",
                "is_staff": True,
                "is_superuser": True,
                "roles": [UserRole.ADMIN, UserRole.DISPATCHER],
            },
        )
        admin.set_password("Admin@123456")
        admin.save()
        self.stdout.write(f"Created Admin: {admin.email}")

        # 2. Dispatcher User
        dispatcher, _ = User.objects.get_or_create(
            phone="+923000000002",
            defaults={
                "name": "Live Dispatcher",
                "email": "dispatcher@khanparcel.com",
                "is_staff": True,
                "roles": [UserRole.DISPATCHER],
            },
        )
        dispatcher.set_password("Dispatcher@123456")
        dispatcher.save()
        self.stdout.write(f"Created Dispatcher: {dispatcher.email}")

        # 3. Base Pricing Rules
        for v_type in [VehicleType.BIKE, VehicleType.CAR, VehicleType.VAN, VehicleType.TRUCK]:
            QuoteService.get_or_create_default_rule(v_type, city="Islamabad")
        self.stdout.write("Created Price Rules for all vehicle classes.")

        # 4. Promo Code
        PromoCode.objects.get_or_create(
            code="WELCOME100",
            defaults={
                "description": "100 PKR off on first delivery",
                "discount_type": "FIXED",
                "discount_value": Decimal("100.00"),
                "min_order_amount": Decimal("200.00"),
                "valid_to": timezone.now() + timezone.timedelta(days=365),
            },
        )

        # 5. Seed 20 Riders in Islamabad/Rawalpindi
        names = ["Zubair Khan", "Hamza Farooq", "Bilal Mustafa", "Usman Ali", "Tariq Mahmood", "Kamran Shah", "Faisal Raza", "Arslan Qureshi", "Waqas Ahmed", "Imran Abbasi"]
        for i, name in enumerate(names):
            phone = f"+9230100000{i:02d}"
            rider_user, _ = User.objects.get_or_create(
                phone=phone,
                defaults={"name": name, "roles": [UserRole.RIDER]},
            )
            lat, lng, loc_name = ISLAMABAD_COORDS[i % len(ISLAMABAD_COORDS)]

            profile, _ = RiderProfile.objects.get_or_create(
                user=rider_user,
                defaults={
                    "cnic_number": f"61101-{1000000+i}-1",
                    "license_number": f"DL-ICT-{4000+i}",
                    "review_status": ReviewStatus.APPROVED,
                    "status": RiderStatus.AVAILABLE if i % 3 != 0 else RiderStatus.BUSY,
                    "is_online": True,
                    "current_location": Point(lng, lat, srid=4326),
                    "rating_avg": Decimal(str(round(random.uniform(4.7, 5.0), 2))),
                    "rating_count": random.randint(15, 120),
                    "battery_level": random.randint(50, 98),
                    "last_heartbeat_at": timezone.now(),
                },
            )

            Vehicle.objects.get_or_create(
                rider=profile,
                defaults={
                    "vehicle_type": VehicleType.BIKE,
                    "make": "Honda",
                    "model": "CD70",
                    "year": 2023,
                    "color": "Black",
                    "plate_number": f"ICT-LE-{7000+i}",
                    "is_active": True,
                },
            )

        self.stdout.write("Created 10 active test riders with vehicles and GPS coordinates.")

        # 6. Seed Customers and Orders
        customer_user, _ = User.objects.get_or_create(
            phone="+923009998877",
            defaults={"name": "Test Customer", "roles": [UserRole.CUSTOMER]},
        )

        for i in range(5):
            p_lat, p_lng, p_addr = ISLAMABAD_COORDS[i]
            d_lat, d_lng, d_addr = ISLAMABAD_COORDS[(i + 3) % len(ISLAMABAD_COORDS)]

            quote = QuoteService.create_quote(
                pickup_lat=p_lat,
                pickup_lng=p_lng,
                dropoff_lat=d_lat,
                dropoff_lng=d_lng,
                pickup_address=p_addr,
                dropoff_address=d_addr,
                vehicle_type=VehicleType.BIKE,
                user=customer_user,
            )

            Order.objects.get_or_create(
                quote=quote,
                defaults={
                    "customer": customer_user,
                    "vehicle_type": VehicleType.BIKE,
                    "status": OrderStatus.SEARCHING_RIDER if i == 0 else OrderStatus.DELIVERED,
                    "pickup_point": quote.pickup_point,
                    "dropoff_point": quote.dropoff_point,
                    "pickup_address": p_addr,
                    "dropoff_address": d_addr,
                    "sender_name": "Test Sender",
                    "sender_phone": "+923001234567",
                    "recipient_name": "Test Recipient",
                    "recipient_phone": "+923219876543",
                    "fare_amount": quote.base_price + quote.distance_price,
                    "cod_amount": Decimal("1500.00") if i % 2 == 0 else Decimal("0.00"),
                    "total_amount": quote.total_price,
                    "payment_method": PaymentMethod.COD,
                    "payment_status": PaymentStatus.PAID if i > 0 else PaymentStatus.PENDING,
                    "pickup_otp": "1234",
                    "delivery_otp": "5678",
                },
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Khan Parcel platform!"))
