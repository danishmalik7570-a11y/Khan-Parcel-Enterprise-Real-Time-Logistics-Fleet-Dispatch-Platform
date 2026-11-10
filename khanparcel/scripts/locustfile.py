# =============================================================================
# Khan Parcel — Locust Load & Stress Testing
# =============================================================================
"""
Load testing script to benchmark quote calculation, order creation,
and real-time tracking endpoints under peak concurrent traffic.
Usage: locust -f scripts/locustfile.py --host http://localhost:8000
"""

import random
from locust import HttpUser, task, between

SAMPLE_COORDS = [
    (33.7297, 73.0746, "F-6 Markaz"),
    (33.7214, 73.0564, "F-7 Jinnah Super"),
    (33.7088, 73.0552, "Blue Area"),
    (33.6732, 73.0784, "I-8 Markaz"),
    (33.5971, 73.0538, "Saddar Rawalpindi"),
]


class KhanParcelCustomer(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def calculate_price_quote(self):
        p_lat, p_lng, p_addr = random.choice(SAMPLE_COORDS)
        d_lat, d_lng, d_addr = random.choice(SAMPLE_COORDS)

        self.client.post(
            "/api/v1/pricing/quote/",
            json={
                "pickup_lat": p_lat,
                "pickup_lng": p_lng,
                "dropoff_lat": d_lat,
                "dropoff_lng": d_lng,
                "pickup_address": p_addr,
                "dropoff_address": d_addr,
                "vehicle_type": random.choice(["BIKE", "CAR"]),
            },
            name="/api/v1/pricing/quote/",
        )

    @task(1)
    def check_health(self):
        self.client.get("/healthz/", name="/healthz/")
