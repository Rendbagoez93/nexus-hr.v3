"""
apps/apis/v1/documents/views.py

Employee Document API endpoints (nested under an Employee):
  GET    /api/v1/employees/{employee_id}/documents/       — list
  POST   /api/v1/employees/{employee_id}/documents/       — upload
  GET    /api/v1/employees/{employee_id}/documents/{id}/  — retrieve + signed URL
  PATCH  /api/v1/employees/{employee_id}/documents/{id}/  — update metadata
  DELETE /api/v1/employees/{employee_id}/documents/{id}/  — soft delete
"""

from uuid import UUID

from pydantic import ValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.apis.v1.documents.serializers import (
    EmployeeDocumentDetailSerializer,
    EmployeeDocumentSerializer,
)
from apps.documents.schemas import DocumentCreateSchema, DocumentUpdateSchema
from apps.documents.services import DocumentService
from apps.employees.services.employee_service import EmployeeService
from apps.shared.permissions import IsHRAdmin, IsOwnerOrHRAdmin
from apps.shared.utils.pagination import NexusPaginator


class EmployeeDocumentViewSet(viewsets.ViewSet):
    """
    ViewSet for EmployeeDocument CRUD operations, nested under an Employee.

    Write access (upload/update/delete): HR Admin only.
    Read access (list/retrieve): the employee themselves, or HR Admin.
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsHRAdmin()]
        return [IsAuthenticated(), IsOwnerOrHRAdmin()]

    def _company_id(self, request) -> UUID:
        user = request.user
        if not getattr(user, "company_id", None):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("No company associated with this user.")
        return user.company_id

    def _validation_error_response(self, exc: ValidationError) -> Response:
        """Return a standard error envelope from a Pydantic ValidationError."""
        errors = exc.errors()
        details = {}
        for err in errors:
            loc_tuple = err["loc"]
            if len(loc_tuple) == 1:
                details[str(loc_tuple[0])] = [err["msg"]]
            else:
                key = ".".join(str(p) for p in loc_tuple)
                details[key] = [err["msg"]]
        return Response(
            {
                "error": "validation_error",
                "message": "Request validation failed.",
                "status": 400,
                "details": details,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def list(self, request, employee_pk=None):
        """GET /api/v1/employees/{employee_id}/documents/"""
        company_id = self._company_id(request)
        employee = EmployeeService.get_by_id(employee_pk, company_id)
        self.check_object_permissions(request, employee)

        documents = DocumentService.list_for_employee(employee_pk, company_id)

        paginator = NexusPaginator()
        page = paginator.paginate_queryset(documents, request)
        serializer = EmployeeDocumentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request, employee_pk=None):
        """POST /api/v1/employees/{employee_id}/documents/ — multipart upload."""
        company_id = self._company_id(request)

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {
                    "error": "validation_error",
                    "message": "Request validation failed.",
                    "status": 400,
                    "details": {"file": ["This field is required."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            schema = DocumentCreateSchema.model_validate(request.data)
        except ValidationError as exc:
            return self._validation_error_response(exc)

        document = DocumentService.upload(
            employee_id=employee_pk,
            company_id=company_id,
            file_obj=uploaded_file,
            file_name=uploaded_file.name,
            doc_type=schema.doc_type,
            valid_until=schema.valid_until,
        )

        serializer = EmployeeDocumentSerializer(document)
        return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, employee_pk=None, pk=None):
        """GET /api/v1/employees/{employee_id}/documents/{id}/ — includes signed URL."""
        company_id = self._company_id(request)
        employee = EmployeeService.get_by_id(employee_pk, company_id)
        self.check_object_permissions(request, employee)

        document = DocumentService.get_by_id(pk, employee_pk, company_id)
        serializer = EmployeeDocumentDetailSerializer(document)
        return Response({"data": serializer.data})

    def partial_update(self, request, employee_pk=None, pk=None):
        """PATCH /api/v1/employees/{employee_id}/documents/{id}/"""
        company_id = self._company_id(request)

        try:
            schema = DocumentUpdateSchema.model_validate(request.data)
        except ValidationError as exc:
            return self._validation_error_response(exc)

        fields = schema.model_dump(exclude_unset=True)
        document = DocumentService.update(
            pk=pk, employee_id=employee_pk, company_id=company_id, **fields
        )
        serializer = EmployeeDocumentSerializer(document)
        return Response({"data": serializer.data})

    def destroy(self, request, employee_pk=None, pk=None):
        """DELETE /api/v1/employees/{employee_id}/documents/{id}/ — soft delete."""
        company_id = self._company_id(request)
        DocumentService.soft_delete(pk, employee_pk, company_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
