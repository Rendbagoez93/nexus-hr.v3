"""
apps/attendance/urls_web.py

Web dashboard URL routing for the attendance module.

Included at ``/dashboard/attendance/`` in ``config/urls.py``.
Wire-up: each ``path()`` here corresponds to a view in ``views_web.py``.
"""

from django.urls import path

app_name = "attendance"

urlpatterns = [
    # TODO(feat/attendance): wire up actual views
    # path("", views_web.attendance_dashboard, name="dashboard"),
    # path("logs/", views_web.attendance_logs, name="attendance-logs"),
    # path("logs/<uuid:log_pk>/", views_web.attendance_log_detail, name="attendance-log-detail"),
    # path("shifts/", views_web.shift_list, name="shift-list"),
    # path("shifts/<uuid:shift_pk>/", views_web.shift_detail, name="shift-detail"),
    # path("shift-assignments/", views_web.shift_assignment_list, name="shift-assignments"),
    # path("leave-types/", views_web.leave_type_list, name="leave-type-list"),
    # path("leave-requests/", views_web.leave_request_list, name="leave-request-list"),
    # path("leave-requests/<uuid:pk>/", views_web.leave_request_detail, name="leave-request-detail"),
    # path("leave-balances/", views_web.leave_balance_list, name="leave-balance-list"),
    # path("sites/", views_web.site_list, name="site-list"),
    # path("projects/", views_web.project_list, name="project-list"),
    # path("disputes/", views_web.dispute_list, name="dispute-list"),
]
