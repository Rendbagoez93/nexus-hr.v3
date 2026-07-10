"""
apps/apis/v1/departments/views.py

Department API endpoints:
  GET    /api/v1/departments/          — list (filterable by parent_id, is_active)
  POST   /api/v1/departments/          — create
  GET    /api/v1/departments/{id}/     — retrieve
  PATCH  /api/v1/departments/{id}/     — partial update
  DELETE /api/v1/departments/{id}/     — soft delete
  POST   /api/v1/departments/{id}/restore/ — restore
  GET    /api/v1/departments/tree/     — org-chart tree (nested children)
"""

from uuid import UUID

from pydantic import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.apis.v1.departments.serializers import (
    DepartmentSerializer,
    DepartmentTreeSerializer,
)
from apps.apis.v1.departments.services import DepartmentService
from apps.departments.schemas import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)
from apps.shared.permissions import IsHRAdmin
from apps.shared.utils.pagination import NexusPaginator


class DepartmentViewSet(viewsets.ViewSet):
    """
    ViewSet for Department CRUD operations.
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
        GET /api/v1/departments/
        Query params: parent_id (optional), is_active (optional, default=True)
        """
        company_id = self._company_id(request)
        parent_id = request.query_params.get("parent_id")
        is_active = request.query_params.get("is_active", "true").lower() == "true"

        try:
            parent_id_parsed = UUID(parent_id) if parent_id else None
        except ValueError:
            return Response(
                {"detail": "parent_id must be a valid UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        departments = DepartmentService.list_for_company(
            company_id=company_id,
            parent_id=parent_id_parsed,
            is_active=is_active,
        )

        paginator = NexusPaginator()
        page = paginator.paginate_queryset(departments, request)
        serializer = DepartmentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        """
        POST /api/v1/departments/
        """
        company_id = self._company_id(request)

        try:
            schema = DepartmentCreateRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.error_count() and str(e) or "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        department = DepartmentService.create(
            company_id=company_id,
            name=schema.name,
            code=schema.code,
            parent_id=schema.parent_id,
            created_by=str(request.user.id) if request.user else None,
        )

        serializer = DepartmentSerializer(department)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/departments/{id}/
        """
        company_id = self._company_id(request)
        department = DepartmentService.get_by_id(pk, company_id)
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """
        PATCH /api/v1/departments/{id}/
        """
        company_id = self._company_id(request)

        try:
            schema = DepartmentUpdateRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.error_count() and str(e) or "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fields = schema.model_dump(exclude_unset=True)
        if "parent_id" in fields and fields["parent_id"] == "":
            fields["parent_id"] = None

        department = DepartmentService.update(
            pk=pk,
            company_id=company_id,
            **fields,
        )
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """
        DELETE /api/v1/departments/{id}/ — soft delete
        """
        company_id = self._company_id(request)
        DepartmentService.soft_delete(pk, company_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        POST /api/v1/departments/{id}/restore/
        """
        company_id = self._company_id(request)
        department = DepartmentService.restore(pk, company_id)
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        """
        GET /api/v1/departments/tree/
        Returns root departments with nested children for org-chart display.
        """
        from apps.departments.selectors import DepartmentSelector

        company_id = self._company_id(request)
        roots = DepartmentSelector.with_children(company_id)
        serializer = DepartmentTreeSerializer(roots, many=True)
        return Response(serializer.data)
