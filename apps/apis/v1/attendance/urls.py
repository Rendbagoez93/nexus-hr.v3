"""
apps/apis/v1/attendance/urls.py

Mobile-facing API URL routing for the attendance module.

Wire-up: included at ``api/v1/attendance/`` in ``apps/apis/v1/urls.py``.
"""

from django.urls import path

app_name = "attendance"

urlpatterns = [
    # TODO(feat/attendance): wire up actual DRF viewsets
    # path("logs/", views.clock_in, name="clock-in"),
    # path("logs/<uuid:pk>/", views.attendance_log_detail, name="attendance-log-detail"),
    # path("logs/<uuid:pk>/clock-out/", views.clock_out, name="clock-out"),
    # path("shifts/", views.ShiftViewSet.as_view({"get": "list"}), name="shift-list"),
    # path("shift-assignments/", views.ShiftAssignmentViewSet.as_view({"get": "list", "post": "create"}), name="shift-assignments"),
    # path("sites/", views.SiteViewSet.as_view({"get": "list", "post": "create"}), name="site-list"),
    # path("site-assignments/", views.SiteAssignmentViewSet.as_view({"get": "list", "post": "create"}), name="site-assignments"),
    # path("projects/", views.ProjectViewSet.as_view({"get": "list", "post": "create"}), name="project-list"),
    # path("project-assignments/", views.ProjectAssignmentViewSet.as_view({"get": "list", "post": "create"}), name="project-assignments"),
    # path("leave-types/", views.LeaveTypeViewSet.as_view({"get": "list", "post": "create"}), name="leave-type-list"),
    # path("leave-requests/", views.LeaveRequestViewSet.as_view({"get": "list", "post": "create"}), name="leave-request-list"),
    # path("leave-requests/<uuid:pk>/", views.LeaveRequestViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="leave-request-detail"),
    # path("leave-requests/<uuid:pk>/approve/", views.approve_leave_request, name="leave-request-approve"),
    # path("leave-requests/<uuid:pk>/reject/", views.reject_leave_request, name="leave-request-reject"),
    # path("leave-balances/", views.LeaveBalanceViewSet.as_view({"get": "list"}), name="leave-balance-list"),
    # path("disputes/", views.AttendanceDisputeViewSet.as_view({"get": "list", "post": "create"}), name="dispute-list"),
    # path("disputes/<uuid:pk>/", views.AttendanceDisputeViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="dispute-detail"),
    # path("me/today/", views.my_today_attendance, name="my-today"),
    # path("me/balance/", views.my_leave_balance, name="my-leave-balance"),
]
