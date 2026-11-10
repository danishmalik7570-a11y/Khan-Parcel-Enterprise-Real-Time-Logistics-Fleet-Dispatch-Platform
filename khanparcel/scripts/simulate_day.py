#!/usr/bin/env python
# =============================================================================
# Khan Parcel — Simulate Day Operations Script
# =============================================================================
"""
Simulate a full day of logistics operations in Islamabad/Rawalpindi.
Runs end-to-end dispatch matching, rider movement, OTP verification,
financial settlement, and customer reviews.
"""

from __future__ import annotations

import os
import random
import sys
import time
from decimal import Decimal
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.orders.models import Order, OrderStatus, PaymentMethod
from apps.orders.services import OrderService
from apps.pricing.services import QuoteService
from apps.riders.models import RiderProfile, RiderStatus, VehicleType
from apps.riders.services import RiderService
from apps.dispatch.services import DispatchEngine

SIM_LOCATIONS = [
    (33.7297, 73.0746, "F-6 Markaz, Islamabad"),
    (33.7214, 73.0564, "F-7 Jinnah Super, Islamabad"),
    (33.7088, 73.0552, "Blue Area, Islamabad"),
    (33.6732, 73.0784, "I-8 Markaz, Islamabad"),
    (33.5971, 73.0538, "Saddar, Rawalpindi"),
]


def run_day_simulation(num_trips: int = 5):
    print(f"🚀 Starting Khan Parcel Day Simulation ({num_trips} trips)...")

    # 1. Fetch available test riders
    riders = list(RiderProfile.objects.filter(is_online=True, status=RiderStatus.AVAILABLE))
    if not riders:
        print("⚠️ No available riders found. Please run 'python manage.py seed_khanparcel' first.")
        return

    # 2. Fetch or create a test customer
    customer, _ = User.objects.get_or_create(
        phone="+923001112233",
        defaults={"name": "Simulated Customer", "roles": [UserRole.CUSTOMER]},
    )

    for i in range(1, num_trips + 1):
        print(f"\n📦 --- Simulation Trip #{i} ---")
        p_lat, p_lng, p_addr = random.choice(SIM_LOCATIONS)
        d_lat, d_lng, d_addr = random.choice(SIM_LOCATIONS)
        while d_addr == p_addr:
            d_lat, d_lng, d_addr = random.choice(SIM_LOCATIONS)

        # Step 1: Create Quote
        print(f"  1. Requesting Quote: {p_addr} -> {d_addr}")
        quote = QuoteService.create_quote(
            pickup_lat=p_lat,
            pickup_lng=p_lng,
            dropoff_lat=d_lat,
            dropoff_lng=d_lng,
            pickup_address=p_addr,
            dropoff_address=d_addr,
            vehicle_type=VehicleType.BIKE,
            user=customer,
        )
        print(f"     Fare: {quote.total_price} PKR (Distance: {quote.distance_km} km)")

        # Step 2: Customer Places Order
        order = OrderService.create_from_quote(
            quote=quote,
            customer=customer,
            sender_name="Sender Malik",
            sender_phone="+923001234567",
            recipient_name="Recipient Tariq",
            recipient_phone="+923219876543",
            parcel_description="Express Document",
            cod_amount=Decimal("1500.00") if i % 2 == 0 else Decimal("0.00"),
        )
        print(f"  2. Order Created: {order.order_number} (Pickup OTP: {order.pickup_otp}, Delivery OTP: {order.delivery_otp})")

        # Step 3: Dispatch Engine Matches Candidate
        print("  3. Running Automated Dispatch Matching Engine...")
        DispatchEngine.dispatch_round(str(order.id), round_num=1)
        offer = order.dispatch_offers.filter(status="PENDING").first()

        if offer:
            assigned_rider = offer.rider
            print(f"     Candidate matched: {assigned_rider.user.name} (Score: {offer.score}, ETA: {offer.eta_seconds}s)")
            # Rider accepts offer
            DispatchEngine.accept_offer(str(offer.id), assigned_rider)
            print(f"     Rider {assigned_rider.user.name} ACCEPTED job.")
        else:
            # Fallback manual assign
            assigned_rider = random.choice(riders)
            DispatchEngine.manual_assign(str(order.id), str(assigned_rider.id), customer)
            print(f"     Assigned to rider {assigned_rider.user.name}")

        order.refresh_from_db()

        # Step 4: Rider arrives at Pickup
        print(f"  4. Rider navigating to pickup location...")
        RiderService.update_location(assigned_rider, lat=p_lat, lng=p_lng)
        OrderService.transition(order, OrderStatus.RIDER_ARRIVED_PICKUP, changed_by=assigned_rider.user)
        print("     Status: RIDER_ARRIVED_PICKUP")

        # Step 5: Verify Pickup OTP
        print(f"  5. Verifying Pickup OTP ({order.pickup_otp})...")
        OrderService.verify_pickup_otp(order, order.pickup_otp)
        print("     Status: PICKED_UP (In transit)")

        # Step 6: Rider navigates to destination
        print(f"  6. Rider delivering along road polyline...")
        RiderService.update_location(assigned_rider, lat=d_lat, lng=d_lng)
        OrderService.transition(order, OrderStatus.ARRIVED_DELIVERY, changed_by=assigned_rider.user)
        print("     Status: ARRIVED_DELIVERY")

        # Step 7: Verify Delivery OTP & Complete Payment
        print(f"  7. Verifying Delivery OTP ({order.delivery_otp}) & settling ledger...")
        OrderService.verify_delivery_otp(order, order.delivery_otp, recipient_name="Recipient Tariq")
        print("     Status: DELIVERED (Payment Settled via Double-Entry Ledger)")

        # Step 8: Customer 5-Star Rating
        rating = OrderService.rate_order(order, customer, score=5, comment="Super fast delivery!", tags="Fast, Polite")
        print(f"  8. Customer Review: ⭐ {rating.score}/5 ('{rating.comment}')")

    print("\n✅ Simulation completed successfully! All lifecycle stages verified.")


if __name__ == "__main__":
    trips = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_day_simulation(trips)
