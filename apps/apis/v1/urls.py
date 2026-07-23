"""
apps/apis/v1/urls.py

Root URL configuration for the v1 API.
"""

from django.urls import include, path

from apps.apis.v1.attendance.urls import urlpatterns as attendance_patterns
from apps.apis.v1.auth.urls import urlpatterns as auth_patterns
from apps.apis.v1.departments.urls import urlpatterns as department_patterns
from apps.apis.v1.documents.urls import urlpatterns as document_patterns
from apps.apis.v1.employees.urls import urlpatterns as employee_patterns
from apps.apis.v1.positions.urls import urlpatterns as position_patterns

urlpatterns = [
    path("auth/", include((auth_patterns, "auth"))),
    path("departments/", include((department_patterns, "department"))),
    path(
        "employees/<uuid:employee_pk>/documents/",
        include((document_patterns, "document")),
    ),
    path("employees/", include((employee_patterns, "employee"))),
    path("positions/", include((position_patterns, "position"))),
    path("attendance/", include((attendance_patterns, "attendance"))),
    # path("violations/", include((hse_patterns, "violation"))),
    # path("man-hours/", include((hse_patterns, "man_hours"))),
    # path("inductions/", include((hse_patterns, "induction"))),
    # path("work-permits/", include((hse_patterns, "work_permit"))),
    # path("payroll-runs/", include((payroll_patterns, "payroll"))),
    # path("payslips/", include((payroll_patterns, "payslip"))),
]
