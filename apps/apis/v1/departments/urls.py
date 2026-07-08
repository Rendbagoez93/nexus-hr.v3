"""
apps/apis/v1/departments/urls.py

URL routing for Department API.
"""

from django.urls import path

from apps.apis.v1.departments.views import DepartmentViewSet

department_list = DepartmentViewSet.as_view({"get": "list", "post": "create"})
department_detail = DepartmentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
department_restore = DepartmentViewSet.as_view({"post": "restore"})
department_tree = DepartmentViewSet.as_view({"get": "tree"})

urlpatterns = [
    path("", department_list, name="department-list"),
    path("tree/", department_tree, name="department-tree"),
    path("<uuid:pk>/", department_detail, name="department-detail"),
    path("<uuid:pk>/restore/", department_restore, name="department-restore"),
]
