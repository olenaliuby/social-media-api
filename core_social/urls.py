from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core_social.views import (
    ProfileViewSet,
    CurrentUserProfileView,
    ProfileFollowersView,
    ProfileFollowingView,
    PostViewSet,
    CommentViewSet,
)

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profiles")
router.register(r"posts", PostViewSet, basename="posts")
router.register(r"posts/(?P<post_id>\d+)/comments", CommentViewSet, "post-comments")


urlpatterns = [
    path("", include(router.urls)),
    path("me/", CurrentUserProfileView.as_view(), name="me"),
    path("me/followers/", ProfileFollowersView.as_view(), name="me_followers"),
    path("me/following/", ProfileFollowingView.as_view(), name="me_following"),
]

app_name = "core_social"
