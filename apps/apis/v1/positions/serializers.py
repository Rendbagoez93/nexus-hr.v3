"""
apps/apis/v1/positions/serializers.py
"""

from rest_framework import serializers

from apps.departments.models import Position


class PositionSerializer(serializers.ModelSerializer):
    """Flat serializer for Position — used in list/retrieve views."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True)

    class Meta:
        model = Position
        fields = [
            "id",
            "company_id",
            "department_id",
            "department_name",
            "department_code",
            "title",
            "level",
            "base_salary_min",
            "base_salary_max",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]
