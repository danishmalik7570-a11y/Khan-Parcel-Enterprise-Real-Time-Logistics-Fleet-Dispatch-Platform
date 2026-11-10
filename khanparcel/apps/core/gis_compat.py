# =============================================================================
# Khan Parcel — GIS Compatibility Layer
# =============================================================================
# Gracefully falls back to standard fields and a Python Point class
# when GDAL C-libraries are not installed on the host system (e.g. Windows without Docker).
# =============================================================================

from __future__ import annotations

import json
from typing import Any

from django.db import models

try:
    from django.contrib.gis.db import models as _gis_models
    from django.contrib.gis.geos import Point as _GISPoint
    # Test if GDAL actually loads without error
    _test = _GISPoint(0, 0)
    gis_models = _gis_models
    Point = _GISPoint
    HAS_GDAL = True
except Exception:
    HAS_GDAL = False

    class FallbackPoint:
        def __init__(self, x: float = 0.0, y: float = 0.0, srid: int = 4326) -> None:
            self.x = float(x)  # lng
            self.y = float(y)  # lat
            self.srid = srid

        def __str__(self) -> str:
            return f"POINT ({self.x} {self.y})"

        def __repr__(self) -> str:
            return f"<Point: [{self.x}, {self.y}]>"

    class FallbackPointField(models.Field):
        description = "Fallback PointField storing (lng, lat) as JSON string"

        def __init__(self, *args: Any, srid: int = 4326, **kwargs: Any) -> None:
            self.srid = srid
            kwargs.setdefault("max_length", 100)
            kwargs.setdefault("null", True)
            kwargs.setdefault("blank", True)
            super().__init__(*args, **kwargs)

        def get_internal_type(self) -> str:
            return "CharField"

        def from_db_value(self, value: Any, expression: Any, connection: Any) -> FallbackPoint | None:
            if value is None:
                return None
            if isinstance(value, FallbackPoint):
                return value
            try:
                coords = json.loads(value)
                return FallbackPoint(coords[0], coords[1], srid=self.srid)
            except Exception:
                return None

        def to_python(self, value: Any) -> FallbackPoint | None:
            if isinstance(value, FallbackPoint) or value is None:
                return value
            try:
                coords = json.loads(value)
                return FallbackPoint(coords[0], coords[1], srid=self.srid)
            except Exception:
                return None

        def get_prep_value(self, value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, FallbackPoint):
                return json.dumps([value.x, value.y])
            return str(value)

    class MockGISModels:
        PointField = FallbackPointField

    gis_models = MockGISModels()
    Point = FallbackPoint

__all__ = ["gis_models", "Point", "HAS_GDAL"]
