"""
apps/apis/v1/employees/urls.py

URL routing for Employee API.
"""

from django.urls import path

from apps.apis.v1.employees.views import EmployeeViewSet, MeViewSet

employee_list = EmployeeViewSet.as_view({"get": "list", "post": "create"})
employee_detail = EmployeeViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
employee_restore = EmployeeViewSet.as_view({"post": "restore"})
employee_deactivate = EmployeeViewSet.as_view({"post": "deactivate"})
me_detail = MeViewSet.as_view({"get": "list"})

urlpatterns = [
    path("", employee_list, name="employee-list"),
    path("me/", me_detail, name="employee-me"),
    path("<uuid:pk>/", employee_detail, name="employee-detail"),
    path("<uuid:pk>/restore/", employee_restore, name="employee-restore"),
    path("<uuid:pk>/deactivate/", employee_deactivate, name="employee-deactivate"),
]
