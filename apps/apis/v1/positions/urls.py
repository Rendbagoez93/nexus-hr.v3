"""
apps/apis/v1/positions/urls.py

URL routing for Position API.
"""

from django.urls import path

from apps.apis.v1.positions.views import PositionViewSet

position_list = PositionViewSet.as_view({"get": "list", "post": "create"})
position_detail = PositionViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
position_restore = PositionViewSet.as_view({"post": "restore"})

urlpatterns = [
    path("", position_list, name="position-list"),
    path("<uuid:pk>/", position_detail, name="position-detail"),
    path("<uuid:pk>/restore/", position_restore, name="position-restore"),
]
