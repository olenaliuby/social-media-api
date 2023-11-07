from django.db.models import Count, Q, OuterRef, Exists, Subquery
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

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
    CommentSerializer,
)
from core_social.permissions import IsAuthorOrReadOnly
from core_social.tasks import create_scheduled_post


class CurrentUserProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Profile.objects.filter(user=self.request.user)
            .select_related("user")
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
        queryset = (
            Profile.objects.prefetch_related(
                "following__following", "followers__follower"
            )
            .select_related("user")
            .annotate(
                followed_by_me=Exists(
                    FollowingRelationships.objects.filter(
                        follower__user=self.request.user, following=OuterRef("pk")
                    )
                ),
                followers_count=Count("followers"),
                following_count=Count("following"),
            )
        )

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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "username",
                type=OpenApiTypes.STR,
                description="Filter by username example: ?username=john",
            ),
            OpenApiParameter(
                "first_name",
                type=OpenApiTypes.STR,
                description="Filter by first name example: ?first_name=john",
            ),
            OpenApiParameter(
                "last_name",
                type=OpenApiTypes.STR,
                description="Filter by last name example: ?last_name=john",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        if self.action == "upload_image":
            return PostImageSerializer
        return PostSerializer

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

        content = self.request.query_params.get("content")
        author_username = self.request.query_params.get("author_username")

        if author_username is not None:
            queryset = queryset.filter(author__username__icontains=author_username)

        if content is not None:
            queryset = queryset.filter(content__icontains=content)

        return queryset

    def perform_create(self, serializer):
        scheduled_at = self.request.data.get("scheduled_at")

        if scheduled_at:
            serializer.validated_data["author_id"] = self.request.user.profile.id
            create_scheduled_post.apply_async(
                args=[serializer.validated_data], eta=scheduled_at
            )
        else:
            serializer.save(author=self.request.user.profile)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "content",
                type=OpenApiTypes.STR,
                description="Filter by content example: ?content=hello",
            ),
            OpenApiParameter(
                "author_username",
                type=OpenApiTypes.STR,
                description="Filter by author username example: ?author_username=john",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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

    @action(
        methods=["POST"],
        detail=True,
        url_path="like",
    )
    def like(self, request, pk=None):
        """Endpoint to like a post"""
        post = get_object_or_404(Post, pk=pk)
        user_profile = request.user.profile
        if Like.objects.filter(profile=user_profile, post=post).exists():
            return Response(
                {"detail": "You have already liked this post."},
                status=status.HTTP_409_CONFLICT,
            )
        Like.objects.create(profile=user_profile, post=post)
        return Response(
            {"detail": "You liked this post."}, status=status.HTTP_204_NO_CONTENT
        )

    @action(
        methods=["POST"],
        detail=True,
        url_path="unlike",
    )
    def unlike(self, request, pk=None):
        """Endpoint to unlike a post"""
        post = get_object_or_404(Post, pk=pk)
        user_profile = request.user.profile
        try:
            like = Like.objects.get(profile=user_profile, post=post)
            like.delete()
            return Response(
                {"detail": "You unliked this post."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Like.DoesNotExist:
            return Response(
                {"detail": "You have not liked this post."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(
        methods=["GET"],
        detail=False,
        url_path="my-posts",
    )
    def my_posts(self, request):
        """Endpoint to get all posts from the user"""
        user_profile = request.user.profile
        queryset = self.get_queryset().filter(author=user_profile)
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        methods=["GET"],
        detail=False,
        url_path="feed",
    )
    def feed(self, request):
        """Endpoint to get all posts from followed users"""
        user_profile = request.user.profile
        followed_profiles = user_profile.following.values_list("following", flat=True)
        queryset = self.get_queryset().filter(author__in=followed_profiles)
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        methods=["GET"],
        detail=False,
        url_path="liked",
    )
    def liked(self, request):
        """Endpoint to get all posts liked by the user"""
        user_profile = request.user.profile
        queryset = self.get_queryset().filter(likes__profile=user_profile)
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def get_queryset(self):
        queryset = Comment.objects.select_related("author", "post").filter(
            post_id=self.kwargs["post_id"]
        )
        return queryset

    def perform_create(self, serializer):
        post = get_object_or_404(Post, id=self.kwargs.get("post_id"))
        serializer.save(author=self.request.user.profile, post=post)
