from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Profile, FollowingRelationships, Post, Comment


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile model with update method for profile image"""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "profile_image",
            "user_email",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "birth_date",
            "bio",
            "followers_count",
            "following_count",
        )

    def update(self, instance, validated_data):
        """If image is not included in request, don't update the image field"""
        if "profile_image" not in validated_data or not validated_data["profile_image"]:
            validated_data["profile_image"] = instance.profile_image
        return super().update(instance, validated_data)


class ProfileListSerializer(ProfileSerializer):
    full_name = serializers.SerializerMethodField()
    followed_by_me = serializers.BooleanField(read_only=True)

    class Meta:
        model = Profile
        fields = ("id", "profile_image", "full_name", "username", "followed_by_me")

    @extend_schema_field(OpenApiTypes.STR)
    def get_full_name(self, obj):
        return obj.full_name


class FollowingRelationshipSerializer(serializers.ModelSerializer):
    profile_id = serializers.IntegerField(source="following.id", read_only=True)
    username = serializers.CharField(source="following.username")

    class Meta:
        model = FollowingRelationships
        fields = ("profile_id", "username")


class FollowerRelationshipSerializer(serializers.ModelSerializer):
    profile_id = serializers.IntegerField(source="follower.id", read_only=True)
    username = serializers.CharField(source="follower.username")

    class Meta:
        model = FollowingRelationships
        fields = ("profile_id", "username")


class ProfileDetailSerializer(ProfileSerializer):
    followers = FollowerRelationshipSerializer(many=True, read_only=True)
    following = FollowingRelationshipSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "profile_image",
            "user_email",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "birth_date",
            "bio",
            "followers",
            "following",
        )


class CommentSerializer(serializers.ModelSerializer):
    post_id = serializers.IntegerField(source="post.id", read_only=True)
    author_username = serializers.CharField(source="author.username", read_only=True)
    commented_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author_username", "post_id", "content", "commented_at")


class LikeSerializer(serializers.ModelSerializer):
    liked_by = serializers.CharField(source="profile.username", read_only=True)

    class Meta:
        model = Post
        fields = ("id", "liked_by")


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "image")


class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_full_name = serializers.CharField(source="author.full_name", read_only=True)
    author_image = serializers.ImageField(source="author.profile_image", read_only=True)
    image = serializers.ImageField(required=False, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    scheduled_at = serializers.DateTimeField(required=False, write_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author_username",
            "author_full_name",
            "author_image",
            "content",
            "created_at",
            "image",
            "likes_count",
            "comments_count",
            "scheduled_at",
        )


class PostListSerializer(PostSerializer):
    liked_by_user = serializers.BooleanField(read_only=True)

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ("liked_by_user",)


class PostDetailSerializer(PostSerializer):
    liked_by_user = serializers.BooleanField(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes = LikeSerializer(many=True, read_only=True)

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + (
            "liked_by_user",
            "comments",
            "likes",
        )
