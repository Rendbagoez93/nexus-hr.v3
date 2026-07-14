"""
apps/employees/services/employee_service.py

Business logic for Employee CRUD operations.
All methods are company-scoped (tenant isolation enforced).
Auto-generates emp_number in NXS-0001 format (unique per company).
Supports optional AuthUser creation within the same transaction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction

from apps.companies.models import Company
from apps.employees.exceptions import EmployeeError
from apps.employees.models import Employee
from apps.users.models import AuthUser

if TYPE_CHECKING:
    from uuid import UUID


class EmployeeService:
    """Handles Employee operations for a given company."""

    @staticmethod
    def _generate_emp_number(company: Company) -> str:
        """
        Generate the next employee number for a company.

        Format: <EMP_PREFIX>-<padded_sequence>
        e.g. NXS-0001, ACME-0042
        """
        prefix = company.emp_number_prefix or "NXS"
        last_employee = (
            Employee.objects.filter(company=company)
            .order_by("-emp_number")
            .values_list("emp_number", flat=True)
            .first()
        )
        if last_employee and "-" in last_employee:
            try:
                last_seq = int(last_employee.split("-")[-1])
                next_seq = last_seq + 1
            except ValueError:
                next_seq = 1
        else:
            next_seq = 1
        return f"{prefix}-{next_seq:04d}"

    @staticmethod
    def list_for_company(
        company_id: UUID,
        status: str | None = None,
        department_id: UUID | None = None,
        is_active: bool | None = None,
    ):
        """
        List employees for a company with optional filters.

        Parameters
        ----------
        company_id: Company UUID
        status: Filter by EmployeeStatus value (active, inactive, resigned, terminated)
        department_id: Filter by department UUID
        is_active: Filter by soft-delete status (True=alive, False=deleted, None=no filter)
        """
        qs = Employee.objects.for_company(company_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if status:
            qs = qs.filter(status=status)
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.select_related(
            "department", "position", "direct_manager", "company"
        ).order_by("emp_number")

    @staticmethod
    def get_by_id(pk: UUID, company_id: UUID) -> Employee:
        """
        Fetch a single employee, enforcing company boundary.

        Raises 403 when the employee exists but belongs to another company,
        so cross-tenant requests never confirm or deny existence.
        """
        try:
            return (
                Employee.objects.for_company(company_id)
                .select_related("department", "position", "direct_manager", "company")
                .get(pk=pk)
            )
        except Employee.DoesNotExist:
            if Employee.objects.filter(pk=pk).exclude(company_id=company_id).exists():
                raise EmployeeError(
                    detail="You do not have access to this employee.",
                    status_code=403,
                )
            raise EmployeeError(detail="Employee not found.", status_code=404)

    @staticmethod
    def get_by_user(user_id: UUID) -> Employee:
        """Fetch the employee linked to an AuthUser."""
        try:
            return Employee.objects.select_related(
                "department", "position", "direct_manager", "company"
            ).get(user_id=user_id)
        except Employee.DoesNotExist:
            raise EmployeeError(
                detail="No employee profile found for this user.",
                status_code=404,
            )

    @staticmethod
    def _validate_create(
        company_id: UUID,
        email: str,
        department_id: UUID | None = None,
        position_id: UUID | None = None,
        direct_manager_id: UUID | None = None,
        create_user: bool = False,
        user_email: str | None = None,
    ) -> Company:
        """Shared validation for create operations. Returns the Company object."""
        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            raise EmployeeError(detail="Company not found.", status_code=404)

        if Employee.objects.filter(company=company, email=email).exists():
            raise EmployeeError(
                detail="An employee with this email already exists in the company.",
                status_code=400,
            )

        if create_user:
            if not user_email:
                raise EmployeeError(
                    detail="user_email is required when create_user is true.",
                    status_code=400,
                )
            if AuthUser.objects.filter(email=user_email).exists():
                raise EmployeeError(
                    detail="An AuthUser with this email already exists.",
                    status_code=400,
                )

        return company

    @staticmethod
    @transaction.atomic
    def create(
        company_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        join_date,
        phone: str = "",
        mobile_phone: str = "",
        gender: str = "other",
        date_of_birth=None,
        place_of_birth: str = "",
        id_card_address: str = "",
        residential_address: str = "",
        department_id: UUID | None = None,
        position_id: UUID | None = None,
        status: str = "active",
        employment_type: str = "permanent",
        base_salary=None,
        direct_manager_id: UUID | None = None,
        create_user: bool = False,
        user_email: str | None = None,
        user_password: str | None = None,
        created_by: str | None = None,
    ) -> Employee:
        """
        Create a new employee, optionally with an AuthUser, in a single transaction.

        Parameters
        ----------
        create_user: If True, create a linked AuthUser for this employee.
        user_email: Email for the AuthUser (required if create_user=True).
        user_password: Password for the AuthUser (required if create_user=True).
        """
        company = EmployeeService._validate_create(
            company_id=company_id,
            email=email,
            department_id=department_id,
            position_id=position_id,
            direct_manager_id=direct_manager_id,
            create_user=create_user,
            user_email=user_email,
        )

        emp_number = EmployeeService._generate_emp_number(company)

        employee = Employee(
            company=company,
            emp_number=emp_number,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            mobile_phone=mobile_phone,
            gender=gender,
            date_of_birth=date_of_birth,
            place_of_birth=place_of_birth,
            id_card_address=id_card_address,
            residential_address=residential_address,
            status=status,
            employment_type=employment_type,
            join_date=join_date,
            base_salary=base_salary,
        )

        if department_id:
            from apps.departments.models import Department

            try:
                employee.department = Department.objects.for_company(company_id).get(
                    pk=department_id
                )
            except Department.DoesNotExist:
                raise EmployeeError(
                    detail="Department not found.", status_code=404
                )

        if position_id:
            from apps.departments.models import Position

            try:
                employee.position = Position.objects.for_company(company_id).get(
                    pk=position_id
                )
            except Position.DoesNotExist:
                raise EmployeeError(detail="Position not found.", status_code=404)

        if direct_manager_id:
            try:
                employee.direct_manager = Employee.objects.for_company(company_id).get(
                    pk=direct_manager_id
                )
            except Employee.DoesNotExist:
                raise EmployeeError(
                    detail="Direct manager not found.", status_code=404
                )

        created_user: AuthUser | None = None
        if create_user:
            created_user = AuthUser.objects.create_user(
                email=user_email,
                password=user_password,
                company_id=company_id,
                role="employee",
            )
            employee.user = created_user

        try:
            employee.save()
        except IntegrityError:
            raise EmployeeError(
                detail="Failed to create employee. Please check for duplicate data.",
                status_code=400,
            )

        return employee

    @staticmethod
    @transaction.atomic
    def update(pk: UUID, company_id: UUID, **fields) -> Employee:
        """Update an employee's fields."""
        employee = EmployeeService.get_by_id(pk, company_id)

        if "email" in fields and fields["email"]:
            new_email = fields["email"]
            if (
                new_email != employee.email
                and Employee.objects.filter(company=company_id, email=new_email)
                .exclude(pk=pk)
                .exists()
            ):
                raise EmployeeError(
                    detail="An employee with this email already exists in the company.",
                    status_code=400,
                )

        for field_name, value in fields.items():
            if field_name in ("department_id", "position_id", "direct_manager_id"):
                continue
            if value is not None and hasattr(employee, field_name):
                setattr(employee, field_name, value)

        if "department_id" in fields:
            department_id = fields["department_id"]
            if department_id is None:
                employee.department = None
            else:
                from apps.departments.models import Department

                try:
                    employee.department = Department.objects.for_company(
                        company_id
                    ).get(pk=department_id)
                except Department.DoesNotExist:
                    raise EmployeeError(
                        detail="Department not found.", status_code=404
                    )

        if "position_id" in fields:
            position_id = fields["position_id"]
            if position_id is None:
                employee.position = None
            else:
                from apps.departments.models import Position

                try:
                    employee.position = Position.objects.for_company(company_id).get(
                        pk=position_id
                    )
                except Position.DoesNotExist:
                    raise EmployeeError(detail="Position not found.", status_code=404)

        if "direct_manager_id" in fields:
            direct_manager_id = fields["direct_manager_id"]
            if direct_manager_id is None:
                employee.direct_manager = None
            else:
                try:
                    employee.direct_manager = Employee.objects.for_company(
                        company_id
                    ).get(pk=direct_manager_id)
                except Employee.DoesNotExist:
                    raise EmployeeError(
                        detail="Direct manager not found.", status_code=404
                    )

        employee.save()
        return employee

    @staticmethod
    @transaction.atomic
    def soft_delete(pk: UUID, company_id: UUID) -> Employee:
        """Soft-delete an employee (deactivate)."""
        employee = EmployeeService.get_by_id(pk, company_id)
        employee.deactivate()
        return employee

    @staticmethod
    @transaction.atomic
    def restore(pk: UUID, company_id: UUID) -> Employee:
        """Restore a soft-deleted employee."""
        try:
            employee = Employee.objects.for_company(company_id).get(
                pk=pk, is_active=False
            )
        except Employee.DoesNotExist:
            if Employee.objects.filter(pk=pk).exclude(company_id=company_id).exists():
                raise EmployeeError(
                    detail="Employee not found or already active.",
                    status_code=403,
                )
            raise EmployeeError(
                detail="Employee not found or already active.", status_code=404
            )
        employee.restore()
        return employee

    @staticmethod
    @transaction.atomic
    def deactivate(
        pk: UUID,
        company_id: UUID,
        resign_date=None,
        termination_reason: str = "",
    ) -> Employee:
        """
        Deactivate an employee: set status=resigned and record resign_date.
        Sets is_active=False as a side-effect of the status change (via model property).
        """
        employee = EmployeeService.get_by_id(pk, company_id)

        if employee.status == "terminated":
            raise EmployeeError(
                detail="Employee is already terminated and cannot be deactivated.",
                status_code=400,
            )

        employee.status = "resigned"
        if resign_date:
            employee.resign_date = resign_date
        if termination_reason:
            employee.termination_reason = termination_reason

        employee.save()
        return employee
