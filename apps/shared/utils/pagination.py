"""
apps/shared/utils/pagination.py

Standardized pagination for the Nexus API.
"""

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class NexusPaginator(PageNumberPagination):
    """
    Default pagination for Nexus API endpoints.

    - page_size: 25 (default)
    - page_size_query_param: "page_size"
    - max_page_size: 100
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema: dict) -> dict:
        return {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "example": 200},
                "next": {
                    "type": "string",
                    "nullable": True,
                    "example": "http://api.example.com/employees/?page=2",
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "example": None,
                },
                "results": schema,
            },
        }
