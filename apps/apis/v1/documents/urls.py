"""
apps/apis/v1/documents/urls.py

URL routing for EmployeeDocument API — nested under Employee.
Included by apps/apis/v1/urls.py at 'employees/<uuid:employee_pk>/documents/'.
"""

from django.urls import path

from apps.apis.v1.documents.views import EmployeeDocumentViewSet

document_list = EmployeeDocumentViewSet.as_view({"get": "list", "post": "create"})
document_detail = EmployeeDocumentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("", document_list, name="document-list"),
    path("<uuid:pk>/", document_detail, name="document-detail"),
]
