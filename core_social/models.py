from django.db import models
from django.conf import settings

from core_social.upload_to_path import UploadToPath


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    username = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    bio = models.TextField(blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    profile_image = models.ImageField(
        blank=True, null=True, upload_to=UploadToPath("profile-images/")
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name_plural = "profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class FollowingRelationships(models.Model):
    follower = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="following"
    )
    following = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="followers"
    )
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class Post(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(
        blank=True, null=True, upload_to=UploadToPath("post-images/")
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post by {self.author} at {self.created_at}"


class Comment(models.Model):
    author = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="comments"
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    commented_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-commented_at"]

    def __str__(self):
        return f"Comment by {self.author} at {self.commented_at}"


class Like(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "post")
        ordering = ["-liked_at"]

    def __str__(self):
        return f"Like by {self.profile} at {self.liked_at}"
