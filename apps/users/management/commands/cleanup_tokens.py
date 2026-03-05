from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken


class Command(BaseCommand):
    help = 'Delete expired JWT tokens and related blacklist entries.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_tokens = OutstandingToken.objects.filter(expires_at__lt=now)
        expired_blacklist = BlacklistedToken.objects.filter(token__in=expired_tokens)
        blacklisted_count = expired_blacklist.count()
        token_count = expired_tokens.count()
        expired_blacklist.delete()
        expired_tokens.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Deleted {token_count} expired tokens and {blacklisted_count} blacklist entries.'
        ))
