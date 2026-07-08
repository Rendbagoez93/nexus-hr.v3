"""
apps/departments/serializers.py

DRF serializers for Department and Position API responses.
"""

from rest_framework import serializers

from apps.departments.models import Department, Position


class DepartmentSerializer(serializers.ModelSerializer):
    """Flat serializer for Department — used in list/retrieve views."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id",
            "company_id",
            "code",
            "name",
            "parent_id",
            "is_active",
            "children",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company_id", "created_at", "updated_at"]

    def get_children(self, obj: Department) -> list[dict]:
        children_qs = obj.children.filter(is_active=True).order_by("name")
        return [
            {
                "id": str(child.id),
                "name": child.name,
                "code": child.code,
                "parent_id": str(child.parent_id) if child.parent_id else None,
                "is_active": child.is_active,
            }
            for child in children_qs
        ]


class DepartmentTreeSerializer(serializers.ModelSerializer):
    """
    Recursive serializer for org-chart tree representation.
    Returns nested children up to one level deep.
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "code", "name", "parent_id", "is_active", "children"]
        read_only_fields = fields

    def get_children(self, obj: Department) -> list[dict]:
        children_qs = obj.children.filter(is_active=True).order_by("name")
        return [
            {
                "id": str(child.id),
                "code": child.code,
                "name": child.name,
                "parent_id": str(child.parent_id) if child.parent_id else None,
                "is_active": child.is_active,
            }
            for child in children_qs
        ]


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
