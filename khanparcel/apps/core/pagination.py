# =============================================================================
# Khan Parcel — Core Pagination
# =============================================================================

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Standard page-number pagination with configurable page size."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list[Any]) -> Response:
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("total_pages", self.page.paginator.num_pages),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class CursorPaginationByCreated(CursorPagination):
    """
    Cursor-based pagination ordered by creation time.

    Best for infinite scroll / real-time feeds where new items
    can be inserted while paginating.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"


class CursorPaginationByTimestamp(CursorPagination):
    """Cursor-based pagination ordered by a generic timestamp field."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = "-at"
    cursor_query_param = "cursor"
