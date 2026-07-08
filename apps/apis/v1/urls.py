"""
apps/apis/v1/urls.py

Root URL configuration for the v1 API.
"""

from django.urls import include, path

from apps.apis.v1.auth.urls import urlpatterns as auth_patterns

urlpatterns = [
    path("auth/", include((auth_patterns, "auth"))),
    # path("companies/", include((core_patterns, "core"))),
    # path("departments/", include((core_patterns, "department"))),
    # path("positions/", include((core_patterns, "position"))),
    # path("employees/", include((core_patterns, "employee"))),
    # path("attendance-logs/", include((attendance_patterns, "attendance"))),
    # path("shifts/", include((attendance_patterns, "shift"))),
    # path("leave-requests/", include((attendance_patterns, "leave"))),
    # path("violations/", include((hse_patterns, "violation"))),
    # path("man-hours/", include((hse_patterns, "man_hours"))),
    # path("inductions/", include((hse_patterns, "induction"))),
    # path("work-permits/", include((hse_patterns, "work_permit"))),
    # path("payroll-runs/", include((payroll_patterns, "payroll"))),
    # path("payslips/", include((payroll_patterns, "payslip"))),
]
