# =============================================================================
# Khan Parcel — Business Views
# =============================================================================

from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.business.models import BulkBatchStatus, BulkOrderBatch, BusinessProfile
from apps.business.serializers import BulkOrderBatchSerializer, BusinessProfileSerializer
from apps.orders.services import OrderService
from apps.pricing.services import QuoteService


class BusinessProfileView(APIView):
    """Retrieve or register corporate merchant profile."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: BusinessProfileSerializer}, tags=["Business"], summary="My Business Profile")
    def get(self, request: Request) -> Response:
        profile, _ = BusinessProfile.objects.get_or_create(
            user=request.user,
            defaults={"company_name": request.user.name or "My Business"},
        )
        return Response(BusinessProfileSerializer(profile).data)

    @extend_schema(request=BusinessProfileSerializer, responses={200: BusinessProfileSerializer}, tags=["Business"], summary="Update Business Profile")
    def put(self, request: Request) -> Response:
        profile, _ = BusinessProfile.objects.get_or_create(
            user=request.user,
            defaults={"company_name": request.user.name or "My Business"},
        )
        serializer = BusinessProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if UserRole.BUSINESS not in request.user.roles:
            request.user.add_role(UserRole.BUSINESS)
        return Response(serializer.data)


class BulkOrderUploadView(APIView):
    """Upload bulk delivery orders via CSV file."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
                "required": ["file"],
            }
        },
        responses={201: BulkOrderBatchSerializer},
        tags=["Business"],
        summary="Upload Bulk CSV Orders",
    )
    def post(self, request: Request) -> Response:
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "CSV file is required."}, status=status.HTTP_400_BAD_REQUEST)

        profile, _ = BusinessProfile.objects.get_or_create(
            user=request.user,
            defaults={"company_name": request.user.name or "My Business"},
        )

        batch = BulkOrderBatch.objects.create(
            business=profile,
            file=file_obj,
            status=BulkBatchStatus.PROCESSING,
        )

        # Process CSV contents synchronously or queued
        try:
            file_obj.seek(0)
            decoded = file_obj.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))

            rows = list(reader)
            batch.total_count = len(rows)
            errors = []
            success_count = 0

            for idx, row in enumerate(rows, start=1):
                try:
                    pickup_lat = float(row.get("pickup_lat", 33.6844))
                    pickup_lng = float(row.get("pickup_lng", 73.0479))
                    dropoff_lat = float(row.get("dropoff_lat", 33.7100))
                    dropoff_lng = float(row.get("dropoff_lng", 73.0600))

                    quote = QuoteService.create_quote(
                        pickup_lat=pickup_lat,
                        pickup_lng=pickup_lng,
                        dropoff_lat=dropoff_lat,
                        dropoff_lng=dropoff_lng,
                        pickup_address=row.get("pickup_address", "Warehouse"),
                        dropoff_address=row.get("dropoff_address", "Customer Location"),
                        vehicle_type=row.get("vehicle_type", "BIKE"),
                        user=request.user,
                    )

                    OrderService.create_from_quote(
                        quote=quote,
                        customer=request.user,
                        sender_name=profile.company_name,
                        sender_phone=str(request.user.phone),
                        recipient_name=row.get("recipient_name", "Recipient"),
                        recipient_phone=row.get("recipient_phone", "+923001234567"),
                        parcel_description=row.get("description", "Bulk Goods"),
                        parcel_weight_kg=Decimal(row.get("weight_kg", "1.0")),
                        cod_amount=Decimal(row.get("cod_amount", "0.0")),
                    )
                    success_count += 1
                except Exception as ex:
                    errors.append({"row": idx, "error": str(ex)})

            batch.processed_count = len(rows)
            batch.success_count = success_count
            batch.error_count = len(errors)
            batch.error_log = errors
            batch.status = BulkBatchStatus.COMPLETED if not errors else BulkBatchStatus.COMPLETED
            batch.save()

        except Exception as e:
            batch.status = BulkBatchStatus.FAILED
            batch.error_log = [{"error": str(e)}]
            batch.save()

        return Response(BulkOrderBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class BulkBatchListView(generics.ListAPIView):
    """List historical bulk order upload batches."""

    serializer_class = BulkOrderBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        profile = get_object_or_404(BusinessProfile, user=self.request.user)
        return BulkOrderBatch.objects.filter(business=profile).order_by("-created_at")
