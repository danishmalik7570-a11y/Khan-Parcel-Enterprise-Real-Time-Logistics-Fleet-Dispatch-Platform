# =============================================================================
# Khan Parcel — Orders Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.orders.models import (
    Order,
    OrderRating,
    OrderStatus,
    OrderStatusLog,
    ParcelType,
    PaymentMethod,
    PaymentStatus,
)
from apps.riders.serializers import RiderProfileSerializer


class OrderStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.name", read_only=True)

    class Meta:
        model = OrderStatusLog
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by",
            "changed_by_name",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class OrderRatingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = OrderRating
        fields = [
            "id",
            "score",
            "comment",
            "tags",
            "customer_name",
            "created_at",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    rider = RiderProfileSerializer(read_only=True)
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)
    rating = OrderRatingSerializer(read_only=True)

    pickup_lat = serializers.SerializerMethodField()
    pickup_lng = serializers.SerializerMethodField()
    dropoff_lat = serializers.SerializerMethodField()
    dropoff_lng = serializers.SerializerMethodField()
    route_polyline = serializers.CharField(source="quote.route_polyline", read_only=True, default="")

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer",
            "rider",
            "status",
            "vehicle_type",
            "pickup_address",
            "dropoff_address",
            "pickup_lat",
            "pickup_lng",
            "dropoff_lat",
            "dropoff_lng",
            "route_polyline",
            "sender_name",
            "sender_phone",
            "recipient_name",
            "recipient_phone",
            "instructions",
            "pickup_notes",
            "delivery_notes",
            "parcel_description",
            "parcel_weight_kg",
            "parcel_type",
            "is_fragile",
            "requires_signature",
            "fare_amount",
            "surge_amount",
            "discount_amount",
            "cod_amount",
            "total_amount",
            "payment_method",
            "payment_status",
            "pickup_otp",
            "delivery_otp",
            "proof_of_pickup",
            "proof_of_delivery",
            "signature_image",
            "recipient_signature_name",
            "cancellation_reason",
            "assigned_at",
            "arrived_pickup_at",
            "picked_up_at",
            "arrived_delivery_at",
            "delivered_at",
            "public_tracking_token",
            "status_logs",
            "rating",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "customer",
            "rider",
            "status",
            "fare_amount",
            "surge_amount",
            "discount_amount",
            "total_amount",
            "payment_status",
            "assigned_at",
            "arrived_pickup_at",
            "picked_up_at",
            "arrived_delivery_at",
            "delivered_at",
            "public_tracking_token",
            "status_logs",
            "rating",
            "created_at",
            "updated_at",
        ]

    def get_pickup_lat(self, obj: Order) -> float:
        return obj.pickup_point.y

    def get_pickup_lng(self, obj: Order) -> float:
        return obj.pickup_point.x

    def get_dropoff_lat(self, obj: Order) -> float:
        return obj.dropoff_point.y

    def get_dropoff_lng(self, obj: Order) -> float:
        return obj.dropoff_point.x


class OrderCreateSerializer(serializers.Serializer):
    quote_id = serializers.UUIDField()
    sender_name = serializers.CharField(max_length=150)
    sender_phone = serializers.CharField(max_length=20)
    recipient_name = serializers.CharField(max_length=150)
    recipient_phone = serializers.CharField(max_length=20)
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    pickup_notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    delivery_notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    parcel_description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    parcel_weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=1.0)
    parcel_type = serializers.ChoiceField(choices=ParcelType.choices, default=ParcelType.SMALL_BOX)
    is_fragile = serializers.BooleanField(required=False, default=False)
    requires_signature = serializers.BooleanField(required=False, default=False)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.COD)
    cod_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.0)


class OrderVerifyPickupSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)


class OrderVerifyDeliverySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    recipient_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")


class OrderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


class OrderRateSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    tags = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
