# =============================================================================
# Khan Parcel — Pricing Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.pricing.models import PriceRule, PromoCode, Quote, SurgeCell
from apps.riders.models import VehicleType


class PriceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceRule
        fields = [
            "id",
            "vehicle_type",
            "city",
            "base_fare",
            "base_distance_km",
            "per_km_rate",
            "per_minute_rate",
            "min_fare",
            "cancellation_fee",
            "free_cancellation_window_seconds",
            "waiting_fee_per_minute",
            "free_waiting_time_minutes",
            "is_active",
        ]
        read_only_fields = ["id"]


class SurgeCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgeCell
        fields = [
            "id",
            "h3_index",
            "multiplier",
            "demand_count",
            "supply_count",
            "last_calculated_at",
        ]


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount",
            "min_order_amount",
            "max_uses",
            "times_used",
            "valid_from",
            "valid_to",
            "is_active",
        ]
        read_only_fields = ["id", "times_used"]


class PromoValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=30)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class QuoteRequestSerializer(serializers.Serializer):
    pickup_lat = serializers.FloatField(min_value=-90.0, max_value=90.0)
    pickup_lng = serializers.FloatField(min_value=-180.0, max_value=180.0)
    dropoff_lat = serializers.FloatField(min_value=-90.0, max_value=90.0)
    dropoff_lng = serializers.FloatField(min_value=-180.0, max_value=180.0)
    pickup_address = serializers.CharField(max_length=255)
    dropoff_address = serializers.CharField(max_length=255)
    vehicle_type = serializers.ChoiceField(choices=VehicleType.choices, default=VehicleType.BIKE)
    promo_code = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=50, required=False, default="Islamabad")


class QuoteResponseSerializer(serializers.ModelSerializer):
    pickup_lat = serializers.SerializerMethodField()
    pickup_lng = serializers.SerializerMethodField()
    dropoff_lat = serializers.SerializerMethodField()
    dropoff_lng = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quote
        fields = [
            "id",
            "pickup_address",
            "dropoff_address",
            "pickup_lat",
            "pickup_lng",
            "dropoff_lat",
            "dropoff_lng",
            "vehicle_type",
            "distance_km",
            "duration_minutes",
            "base_price",
            "distance_price",
            "time_price",
            "surge_multiplier",
            "surge_amount",
            "discount_amount",
            "total_price",
            "route_polyline",
            "expires_at",
            "is_expired",
            "is_accepted",
            "created_at",
        ]
        read_only_fields = fields

    def get_pickup_lat(self, obj: Quote) -> float:
        return obj.pickup_point.y

    def get_pickup_lng(self, obj: Quote) -> float:
        return obj.pickup_point.x

    def get_dropoff_lat(self, obj: Quote) -> float:
        return obj.dropoff_point.y

    def get_dropoff_lng(self, obj: Quote) -> float:
        return obj.dropoff_point.x
