"""
apps/apis/v1/employees/views.py

Employee API endpoints:
  GET    /api/v1/employees/           — paginated list (filterable)
  POST   /api/v1/employees/           — create (+ optional AuthUser)
  GET    /api/v1/employees/{id}/      — retrieve
  PATCH  /api/v1/employees/{id}/      — partial update
  POST   /api/v1/employees/{id}/deactivate/ — deactivate (resign)
  GET    /api/v1/me/                  — self-service: own employee record
"""

from uuid import UUID

from pydantic import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.apis.v1.employees.serializers import EmployeeSerializer
from apps.employees.schemas import (
    DeactivateEmployeeSchema,
    EmployeeCreateSchema,
    EmployeeUpdateSchema,
)
from apps.employees.services.employee_service import EmployeeService
from apps.shared.permissions import IsHRAdmin, IsOwnerOrHRAdmin
from apps.shared.utils.pagination import NexusPaginator


class EmployeeViewSet(viewsets.ViewSet):
    """
    ViewSet for Employee CRUD operations.

    Write access: HR Admin only.
    Read access: Any authenticated user within the company.
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "partial_update", "deactivate"]:
            return [IsAuthenticated(), IsHRAdmin()]
        if self.action == "retrieve":
            return [IsAuthenticated(), IsOwnerOrHRAdmin()]
        return [IsAuthenticated()]

    def _company_id(self, request) -> UUID:
        user = request.user
        if not getattr(user, "company_id", None):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("No company associated with this user.")
        return user.company_id

    def _get_employee(self, pk: str, company_id: UUID):
        """
        Fetch employee by pk, enforcing tenant boundary.

        Raises EmployeeError (403/404) on failure — caught by DRF's
        exception handler and converted to a proper Response.
        """
        return EmployeeService.get_by_id(pk, company_id)

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

    def list(self, request):
        """
        GET /api/v1/employees/
        Query params:
          - status: filter by employee status (active, inactive, resigned, terminated)
          - department_id: filter by department UUID
          - is_active: filter by soft-delete status (true/false, default=all)
        """
        company_id = self._company_id(request)

        status_filter = request.query_params.get("status")
        department_id = request.query_params.get("department_id")
        is_active_param = request.query_params.get("is_active")

        if is_active_param is not None:
            is_active = is_active_param.lower() == "true"
        else:
            is_active = None

        try:
            department_id_parsed = UUID(department_id) if department_id else None
        except ValueError:
            return Response(
                {
                    "error": "validation_error",
                    "message": "department_id must be a valid UUID.",
                    "status": 400,
                    "details": {"department_id": ["Must be a valid UUID."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        employees = EmployeeService.list_for_company(
            company_id=company_id,
            status=status_filter,
            department_id=department_id_parsed,
            is_active=is_active,
        )

        paginator = NexusPaginator()
        page = paginator.paginate_queryset(employees, request)
        serializer = EmployeeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        """
        POST /api/v1/employees/
        Creates an Employee, optionally with an AuthUser.
        """
        company_id = self._company_id(request)

        try:
            schema = EmployeeCreateSchema.model_validate(request.data)
        except ValidationError as exc:
            return self._validation_error_response(exc)

        employee = EmployeeService.create(
            company_id=company_id,
            first_name=schema.first_name,
            last_name=schema.last_name,
            email=schema.email,
            phone=schema.phone,
            mobile_phone=schema.mobile_phone,
            gender=schema.gender,
            date_of_birth=schema.date_of_birth,
            place_of_birth=schema.place_of_birth,
            id_card_address=schema.id_card_address,
            residential_address=schema.residential_address,
            department_id=(
                UUID(schema.department_id) if schema.department_id else None
            ),
            position_id=(
                UUID(schema.position_id) if schema.position_id else None
            ),
            status=schema.status,
            employment_type=schema.employment_type,
            join_date=schema.join_date,
            base_salary=schema.base_salary,
            direct_manager_id=(
                UUID(schema.direct_manager_id) if schema.direct_manager_id else None
            ),
            create_user=schema.create_user,
            user_email=schema.user_email,
            user_password=schema.user_password,
            created_by=str(request.user.id) if request.user else None,
        )

        serializer = EmployeeSerializer(employee)
        return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/employees/{id}/
        Permission: IsOwnerOrHRAdmin — enforced via check_object_permissions().
        """
        company_id = self._company_id(request)
        employee = self._get_employee(pk, company_id)
        self.check_object_permissions(request, employee)
        serializer = EmployeeSerializer(employee)
        return Response({"data": serializer.data})

    def partial_update(self, request, pk=None):
        """
        PATCH /api/v1/employees/{id}/
        """
        company_id = self._company_id(request)

        try:
            schema = EmployeeUpdateSchema.model_validate(request.data)
        except ValidationError as exc:
            return self._validation_error_response(exc)

        fields = schema.model_dump(exclude_unset=True)

        # Normalise empty-string UUID fields to None
        for uuid_field in ("department_id", "position_id", "direct_manager_id"):
            if uuid_field in fields and fields[uuid_field] == "":
                fields[uuid_field] = None

        # Convert remaining string UUIDs to UUID objects
        for uuid_field in ("department_id", "position_id", "direct_manager_id"):
            if uuid_field in fields and fields[uuid_field] is not None:
                fields[uuid_field] = UUID(fields[uuid_field])

        employee = EmployeeService.update(pk=pk, company_id=company_id, **fields)
        serializer = EmployeeSerializer(employee)
        return Response({"data": serializer.data})

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        """
        POST /api/v1/employees/{id}/deactivate/
        Sets status to 'resigned' and records resign_date.
        Returns a message envelope (action confirmation).
        """
        company_id = self._company_id(request)

        try:
            schema = DeactivateEmployeeSchema.model_validate(request.data)
        except ValidationError as exc:
            return self._validation_error_response(exc)

        EmployeeService.deactivate(
            pk=pk,
            company_id=company_id,
            resign_date=schema.resign_date,
            termination_reason=schema.termination_reason,
        )
        return Response(
            {"message": "Employee deactivated successfully."},
            status=status.HTTP_200_OK,
        )


class MeViewSet(viewsets.ViewSet):
    """
    Self-service endpoint: returns the current user's employee profile.

    GET /api/v1/me/
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET /api/v1/me/"""
        if not request.user or not request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated

            raise NotAuthenticated()

        user_id = request.user.id
        if not user_id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("User ID not found.")

        employee = EmployeeService.get_by_user(user_id)
        serializer = EmployeeSerializer(employee)
        return Response({"data": serializer.data})
