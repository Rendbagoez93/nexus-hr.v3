"""
apps/apis/v1/documents/serializers.py

DRF serializers for EmployeeDocument API responses.

`file_url` (the raw storage key) is intentionally never exposed — clients
only ever receive a short-lived signed URL via `signed_url` on the detail
serializer.
"""

from rest_framework import serializers

from apps.documents.models import EmployeeDocument


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    """Flat serializer for EmployeeDocument — used in list/create/update views."""

    doc_type_display = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = EmployeeDocument
        fields = [
            "id",
            "employee_id",
            "doc_type",
            "doc_type_display",
            "file_name",
            "valid_until",
            "is_verified",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_id",
            "is_active",
            "created_at",
            "updated_at",
        ]


class EmployeeDocumentDetailSerializer(EmployeeDocumentSerializer):
    """Detail serializer — adds a short-lived pre-signed URL for downloading the file."""

    signed_url = serializers.SerializerMethodField()

    class Meta(EmployeeDocumentSerializer.Meta):
        fields = [*EmployeeDocumentSerializer.Meta.fields, "signed_url"]

    def get_signed_url(self, obj: EmployeeDocument) -> str:
        from apps.documents.services import DocumentService

        return DocumentService.get_signed_url(obj)
