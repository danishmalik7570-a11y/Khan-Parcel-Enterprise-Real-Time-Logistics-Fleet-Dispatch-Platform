# =============================================================================
# Khan Parcel — Pricing & Routing Services
# =============================================================================

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import httpx
import polyline
import structlog
from django.conf import settings
from apps.core.gis_compat import Point
from django.utils import timezone

from apps.accounts.models import User
from apps.pricing.models import (
    DiscountType,
    PriceRule,
    PromoCode,
    Quote,
    SurgeCell,
)
from apps.riders.models import RiderProfile, RiderStatus, VehicleType

logger = structlog.get_logger(__name__)

# Try to import h3 with fallback support for both h3 v3 and v4 APIs
try:
    import h3
    _H3_V4 = hasattr(h3, "latlng_to_cell")
except ImportError:
    h3 = None
    _H3_V4 = False


class RoutingService:
    """Calculates route distance, duration, and encoded polyline."""

    @classmethod
    def get_route(
        cls,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
    ) -> dict[str, Any]:
        # Try OSRM if configured
        if settings.ROUTING_PROVIDER == "osrm" and settings.OSRM_BASE_URL:
            try:
                url = f"{settings.OSRM_BASE_URL.rstrip('/')}/route/v1/driving/{pickup_lng},{pickup_lat};{dropoff_lng},{dropoff_lat}?overview=full&geometries=polyline"
                with httpx.Client(timeout=4.0) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("routes"):
                            route = data["routes"][0]
                            distance_km = Decimal(str(round(route["distance"] / 1000.0, 2)))
                            duration_mins = Decimal(str(round(route["duration"] / 60.0, 2)))
                            return {
                                "distance_km": distance_km,
                                "duration_minutes": duration_mins,
                                "polyline": route.get("geometry", ""),
                            }
            except Exception as e:
                logger.warning("osrm_routing_failed_fallback_to_haversine", error=str(e))

        # Fallback: Haversine distance with 25 km/h urban average speed factor
        dist_km = cls._haversine_distance_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        # Apply 1.25 road curvature routing factor
        road_km = Decimal(str(round(dist_km * 1.25, 2)))
        duration_mins = Decimal(str(round(float(road_km) / 25.0 * 60.0, 2)))
        encoded_poly = polyline.encode([(pickup_lat, pickup_lng), (dropoff_lat, dropoff_lng)])

        return {
            "distance_km": max(road_km, Decimal("0.50")),
            "duration_minutes": max(duration_mins, Decimal("2.00")),
            "polyline": encoded_poly,
        }

    @staticmethod
    def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0  # Earth radius in kilometers
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2.0) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c


class SurgeService:
    """Dynamic supply/demand surge pricing based on H3 spatial hexagon cells."""

    @classmethod
    def get_h3_index(cls, lat: float, lng: float, resolution: int = 8) -> str:
        if h3:
            try:
                if _H3_V4:
                    return h3.latlng_to_cell(lat, lng, resolution)
                return h3.geo_to_h3(lat, lng, resolution)
            except Exception:
                pass
        # Fallback grid cell key if h3 is unavailable
        grid_lat = round(lat, 2)
        grid_lng = round(lng, 2)
        return f"cell_{grid_lat}_{grid_lng}"

    @classmethod
    def get_multiplier(cls, lat: float, lng: float) -> Decimal:
        h3_idx = cls.get_h3_index(lat, lng, settings.SURGE_H3_RESOLUTION)
        cell = SurgeCell.objects.filter(h3_index=h3_idx).first()
        if not cell:
            return Decimal("1.00")
        return min(cell.multiplier, Decimal(str(settings.SURGE_MAX_MULTIPLIER)))

    @classmethod
    def recalculate_cell(cls, h3_idx: str, demand_count: int, supply_count: int) -> SurgeCell:
        """
        Calculate surge multiplier:
        ratio = demand / max(supply, 1)
        multiplier = 1.0 + max(0, (ratio - 1.2) * 0.5) capped at SURGE_MAX_MULTIPLIER
        """
        if supply_count <= 0 and demand_count > 0:
            raw_mult = Decimal(str(settings.SURGE_MAX_MULTIPLIER))
        else:
            ratio = float(demand_count) / max(supply_count, 1)
            if ratio > 1.2:
                added = (ratio - 1.2) * 0.4
                raw_mult = Decimal(str(round(1.0 + added, 2)))
            else:
                raw_mult = Decimal("1.00")

        mult = min(max(raw_mult, Decimal("1.00")), Decimal(str(settings.SURGE_MAX_MULTIPLIER)))

        cell, _ = SurgeCell.objects.update_or_create(
            h3_index=h3_idx,
            defaults={
                "multiplier": mult,
                "demand_count": demand_count,
                "supply_count": supply_count,
                "last_calculated_at": timezone.now(),
            },
        )
        return cell


class QuoteService:
    """Generates guaranteed price quotes for deliveries."""

    @classmethod
    def get_or_create_default_rule(cls, vehicle_type: str, city: str = "Islamabad") -> PriceRule:
        defaults = {
            VehicleType.BIKE: {"base_fare": Decimal("100.00"), "per_km_rate": Decimal("25.00"), "per_minute_rate": Decimal("2.00"), "min_fare": Decimal("100.00")},
            VehicleType.CAR: {"base_fare": Decimal("200.00"), "per_km_rate": Decimal("40.00"), "per_minute_rate": Decimal("4.00"), "min_fare": Decimal("200.00")},
            VehicleType.VAN: {"base_fare": Decimal("400.00"), "per_km_rate": Decimal("60.00"), "per_minute_rate": Decimal("6.00"), "min_fare": Decimal("400.00")},
            VehicleType.TRUCK: {"base_fare": Decimal("800.00"), "per_km_rate": Decimal("90.00"), "per_minute_rate": Decimal("10.00"), "min_fare": Decimal("800.00")},
        }
        config = defaults.get(vehicle_type, defaults[VehicleType.BIKE])

        rule, _ = PriceRule.objects.get_or_create(
            vehicle_type=vehicle_type,
            city=city,
            defaults={
                "base_fare": config["base_fare"],
                "base_distance_km": Decimal("2.00"),
                "per_km_rate": config["per_km_rate"],
                "per_minute_rate": config["per_minute_rate"],
                "min_fare": config["min_fare"],
                "cancellation_fee": Decimal("50.00"),
                "waiting_fee_per_minute": Decimal("5.00"),
                "is_active": True,
            },
        )
        return rule

    @classmethod
    def create_quote(
        cls,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        pickup_address: str,
        dropoff_address: str,
        vehicle_type: str = VehicleType.BIKE,
        user: User | None = None,
        promo_code_str: str | None = None,
        city: str = "Islamabad",
    ) -> Quote:
        rule = cls.get_or_create_default_rule(vehicle_type, city=city)
        route = RoutingService.get_route(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)

        dist_km = route["distance_km"]
        dur_mins = route["duration_minutes"]

        # Base pricing calculation
        base_price = rule.base_fare
        extra_km = max(Decimal("0.00"), dist_km - rule.base_distance_km)
        dist_price = (extra_km * rule.per_km_rate).quantize(Decimal("0.01"))
        time_price = (dur_mins * rule.per_minute_rate).quantize(Decimal("0.01"))

        subtotal = max(rule.min_fare, base_price + dist_price + time_price)

        # Dynamic Surge
        surge_mult = SurgeService.get_multiplier(pickup_lat, pickup_lng)
        surge_amount = Decimal("0.00")
        if surge_mult > Decimal("1.00"):
            surge_amount = ((surge_mult - Decimal("1.00")) * subtotal).quantize(Decimal("0.01"))

        pre_discount_total = subtotal + surge_amount

        # Promo Code validation
        promo = None
        discount_amount = Decimal("0.00")
        if promo_code_str:
            promo_obj = PromoCode.objects.filter(code__iexact=promo_code_str.strip()).first()
            if promo_obj:
                valid, _ = promo_obj.is_valid_for_amount(pre_discount_total)
                if valid:
                    promo = promo_obj
                    discount_amount = promo_obj.calculate_discount(pre_discount_total)

        final_total = max(rule.min_fare, pre_discount_total - discount_amount)
        expiry = timezone.now() + timezone.timedelta(seconds=settings.QUOTE_EXPIRY_SECONDS)

        quote = Quote.objects.create(
            user=user,
            pickup_point=Point(pickup_lng, pickup_lat, srid=4326),
            dropoff_point=Point(dropoff_lng, dropoff_lat, srid=4326),
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            vehicle_type=vehicle_type,
            distance_km=dist_km,
            duration_minutes=dur_mins,
            base_price=base_price,
            distance_price=dist_price,
            time_price=time_price,
            surge_multiplier=surge_mult,
            surge_amount=surge_amount,
            discount_amount=discount_amount,
            promo_code=promo,
            total_price=final_total,
            route_polyline=route["polyline"],
            expires_at=expiry,
        )

        logger.info(
            "quote_created",
            quote_id=str(quote.id),
            total=str(quote.total_price),
            surge=str(surge_mult),
            dist=str(dist_km),
        )
        return quote
