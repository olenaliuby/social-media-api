from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core_social.views import ProfileViewSet, CurrentUserProfileView

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profiles")


urlpatterns = [
    path("", include(router.urls)),
    path("me/", CurrentUserProfileView.as_view(), name="me"),
]

app_name = "core_social"
