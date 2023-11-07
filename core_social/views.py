from django.db.models import Count, Q, OuterRef, Exists, Subquery
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import (
    get_object_or_404,
    RetrieveUpdateDestroyAPIView,
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from core_social.models import Profile, FollowingRelationships, Post, Like, Comment
from core_social.serializers import (
    ProfileSerializer,
    ProfileListSerializer,
    ProfileDetailSerializer,
    FollowerRelationshipSerializer,
    FollowingRelationshipSerializer,
    PostListSerializer,
    PostImageSerializer,
    PostSerializer,
    PostDetailSerializer,
)
from core_social.permissions import IsAuthorOrReadOnly


class CurrentUserProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Profile.objects.filter(user=self.request.user)
            .prefetch_related("following", "followers")
            .annotate(
                followers_count=Count("followers"), following_count=Count("following")
            )
        )

    def get_object(self):
        return get_object_or_404(self.get_queryset())

    def destroy(self, request, *args, **kwargs):
        profile = self.get_object()
        user = profile.user
        response = super().destroy(request, *args, **kwargs)
        user.delete()
        return response


class ProfileViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return ProfileListSerializer
        if self.action == "retrieve":
            return ProfileDetailSerializer
        return ProfileListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        username = self.request.query_params.get("username")
        first_name = self.request.query_params.get("first_name")
        last_name = self.request.query_params.get("last_name")

        if username:
            queryset = queryset.filter(user__username__icontains=username)

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)

        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)

        return queryset

    @action(
        detail=True,
        methods=["POST"],
        url_path="follow",
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
    )
    def follow(self, request, pk=None):
        follower = get_object_or_404(Profile, user=request.user)
        following = get_object_or_404(Profile, pk=pk)

        if follower == following:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if FollowingRelationships.objects.filter(
            follower=follower, following=following
        ).exists():
            return Response(
                {"detail": "You are already following this user."},
                status=status.HTTP_409_CONFLICT,
            )

        FollowingRelationships.objects.create(follower=follower, following=following)
        return Response(
            {"detail": "You started following this user."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="unfollow",
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
    )
    def unfollow(self, request, pk=None):
        follower = get_object_or_404(Profile, user=request.user)
        following = get_object_or_404(Profile, pk=pk)

        try:
            relation = FollowingRelationships.objects.get(
                Q(follower=follower) & Q(following=following)
            )
            relation.delete()
            return Response(
                {"detail": "You have unfollowed this user."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except FollowingRelationships.DoesNotExist:
            return Response(
                {"detail": "You are not following this user."},
                status=status.HTTP_404_NOT_FOUND,
            )


class ProfileFollowersView(ListAPIView):
    serializer_class = FollowerRelationshipSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return user.profile.followers.all()


class ProfileFollowingView(ListAPIView):
    serializer_class = FollowingRelationshipSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return user.profile.following.all()


class PostViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def get_queryset(self):
        user_profile = self.request.user.profile
        queryset = (
            Post.objects.prefetch_related("likes__profile", "comments__author")
            .select_related("author")
            .annotate(
                likes_count=Subquery(
                    Like.objects.filter(post=OuterRef("pk"))
                    .values("post")
                    .annotate(cnt=Count("post"))
                    .values("cnt")
                ),
                comments_count=Subquery(
                    Comment.objects.filter(post=OuterRef("pk"))
                    .values("post")
                    .annotate(cnt=Count("post"))
                    .values("cnt")
                ),
                liked_by_user=Exists(
                    Like.objects.filter(profile=user_profile, post=OuterRef("pk"))
                ),
            )
        )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        if self.action == "upload_image":
            return PostImageSerializer
        return PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.profile)

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        """Endpoint to upload an image to a post"""
        post = get_object_or_404(Post, pk=pk)
        post.image = request.data.get("image")
        post.save()
        return Response(
            {"detail": "Image uploaded successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
