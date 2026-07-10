"""
apps/apis/v1/positions/views.py

Position API endpoints:
  GET    /api/v1/positions/          — list (filterable by department_id, level)
  POST   /api/v1/positions/          — create
  GET    /api/v1/positions/{id}/     — retrieve
  PATCH  /api/v1/positions/{id}/     — partial update
  DELETE /api/v1/positions/{id}/     — soft delete
  POST   /api/v1/positions/{id}/restore/ — restore
"""

from uuid import UUID

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.apis.v1.positions.serializers import PositionSerializer
from apps.apis.v1.positions.services import PositionService
from apps.shared.permissions import IsHRAdmin
from apps.shared.utils.pagination import NexusPaginator


class PositionViewSet(viewsets.ViewSet):
    """
    ViewSet for Position CRUD operations.
    Write access: HR Admin only.
    Read access: Any authenticated user within the company.
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "restore"]:
            return [IsAuthenticated(), IsHRAdmin()]
        return [IsAuthenticated()]

    def _company_id(self, request) -> UUID:
        user = request.user
        if not user.company_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No company associated with this user.")
        return user.company_id

    def list(self, request):
        """
        GET /api/v1/positions/
        Query params: department_id (optional), level (optional), is_active (optional, default=True)
        """
        company_id = self._company_id(request)
        department_id = request.query_params.get("department_id")
        level = request.query_params.get("level")
        is_active = request.query_params.get("is_active", "true").lower() == "true"

        try:
            department_id = UUID(department_id) if department_id else None
        except ValueError:
            return Response(
                {"detail": "department_id must be a valid UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        positions = PositionService.list_for_company(
            company_id=company_id,
            department_id=department_id,
            level=level,
            is_active=is_active,
        )

        paginator = NexusPaginator()
        page = paginator.paginate_queryset(positions, request)
        serializer = PositionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        """
        POST /api/v1/positions/
        """
        from pydantic import ValidationError

        from apps.departments.schemas import PositionCreateRequest

        company_id = self._company_id(request)

        try:
            schema = PositionCreateRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.error_count() and str(e) or "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        position = PositionService.create(
            company_id=company_id,
            department_id=schema.department_id,
            title=schema.title,
            level=schema.level,
            base_salary_min=schema.base_salary_min,
            base_salary_max=schema.base_salary_max,
            created_by=str(request.user.id) if request.user else None,
        )

        serializer = PositionSerializer(position)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/positions/{id}/
        """
        company_id = self._company_id(request)
        position = PositionService.get_by_id(UUID(pk), company_id)
        serializer = PositionSerializer(position)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """
        PATCH /api/v1/positions/{id}/
        """
        from pydantic import ValidationError

        from apps.departments.schemas import PositionUpdateRequest

        company_id = self._company_id(request)

        try:
            schema = PositionUpdateRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.error_count() and str(e) or "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fields = schema.model_dump(exclude_unset=True)

        position = PositionService.update(
            pk=UUID(pk),
            company_id=company_id,
            **fields,
        )
        serializer = PositionSerializer(position)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """
        DELETE /api/v1/positions/{id}/ — soft delete
        """
        company_id = self._company_id(request)
        PositionService.soft_delete(UUID(pk), company_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        POST /api/v1/positions/{id}/restore/
        """
        company_id = self._company_id(request)
        position = PositionService.restore(UUID(pk), company_id)
        serializer = PositionSerializer(position)
        return Response(serializer.data)
