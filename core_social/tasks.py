from celery import shared_task
from core_social.models import Post


@shared_task
def create_scheduled_post(post_data):
    """Create a post with the given data."""
    post_data.pop("scheduled_at", None)
    Post.objects.create(**post_data)
