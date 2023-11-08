from django.core.management.base import BaseCommand
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


class Command(BaseCommand):
    help = "Removes all blacklisted tokens"

    def handle(self, *args, **kwargs):
        BlacklistedToken.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS("Successfully removed all blacklisted tokens")
        )
