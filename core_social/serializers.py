from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from .models import Profile, FollowingRelationships


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
    followed_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ("id", "profile_image", "full_name", "username", "followed_by_me")

    def get_followed_by_me(self, obj):
        request = self.context.get("request", None)
        if request is not None:
            user_profile = get_object_or_404(Profile, user=request.user)
            return obj.followers.filter(follower=user_profile).exists()
        return False


class FollowingRelationshipSerializer(serializers.ModelSerializer):
    profile_id = serializers.IntegerField(source="following.id", read_only=True)
    username = serializers.CharField(source="follower.username")

    class Meta:
        model = FollowingRelationships
        fields = ("profile_id", "username")


class FollowerRelationshipSerializer(serializers.ModelSerializer):
    profile_id = serializers.IntegerField(source="follower.id", read_only=True)
    username = serializers.CharField(source="following.username")

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
