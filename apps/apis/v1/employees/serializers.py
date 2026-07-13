"""
apps/apis/v1/employees/serializers.py

DRF serializers for Employee API responses.
"""

from rest_framework import serializers

from apps.employees.models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    """Flat serializer for Employee — used in list/retrieve/create views."""

    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )
    position_title = serializers.CharField(
        source="position.title", read_only=True, default=None
    )
    direct_manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "company_id",
            "emp_number",
            # Personal Info
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "mobile_phone",
            "gender",
            "date_of_birth",
            "place_of_birth",
            # Address
            "id_card_address",
            "residential_address",
            # Employment Info
            "department_id",
            "department_name",
            "position_id",
            "position_title",
            "status",
            "employment_type",
            "join_date",
            "resign_date",
            "termination_date",
            "termination_reason",
            # Salary & Manager
            "base_salary",
            "direct_manager_id",
            "direct_manager_name",
            # Links
            "user_id",
            # Status
            "is_active",
            "is_billable",
            "is_active_employment",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_id",
            "emp_number",
            "user_id",
            "is_active",
            "is_billable",
            "is_active_employment",
            "created_at",
            "updated_at",
        ]

    def get_direct_manager_name(self, obj: Employee) -> str | None:
        if obj.direct_manager:
            return f"{obj.direct_manager.first_name} {obj.direct_manager.last_name}".strip()
        return None
