import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Idempotently creates a Django superuser from environment variables if it does not already exist.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'cicadaofficail676@gmail.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'Superuser creation skipped: DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD environment variable is not set.'
            ))
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(
                f"Superuser '{username}' already exists in production database. Skipping creation."
            ))
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(
                f"Superuser '{username}' created successfully in production database."
            ))
