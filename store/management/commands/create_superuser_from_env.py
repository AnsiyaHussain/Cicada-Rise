import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Safely and idempotently promotes or creates the single approved Django superuser/admin account from environment variables.'

    def handle(self, *args, **options):
        admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
        admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not admin_email:
            self.stdout.write(self.style.WARNING(
                'Superuser promotion skipped: DJANGO_SUPERUSER_EMAIL environment variable is not configured.'
            ))
            return

        User = get_user_model()

        # 1. Search for existing user ONLY by the approved admin email
        user = User.objects.filter(email__iexact=admin_email).first()

        if user:
            # Found exact user with approved admin email: promote to superuser/staff without touching password or email
            updated = False
            if not user.is_staff:
                user.is_staff = True
                updated = True
            if not user.is_superuser:
                user.is_superuser = True
                updated = True

            if updated:
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"PROMOTION SUCCESS — Existing user '{user.username}' ({user.email}) promoted to superuser/staff in production database without changing password."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"USER VERIFIED — User '{user.username}' ({user.email}) is already an active superuser/staff in production database."
                ))
        else:
            # 2. Approved email does NOT exist in database yet: create new superuser if username and password are provided
            if not admin_username or not admin_password:
                self.stdout.write(self.style.WARNING(
                    f"Superuser creation skipped: No account exists with email '{admin_email}' and DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD is not fully configured."
                ))
                return

            # Check if the configured username is already taken by another user with a different email
            if User.objects.filter(username=admin_username).exists():
                self.stdout.write(self.style.ERROR(
                    f"SUPERUSER CREATION BLOCKED — Username '{admin_username}' already belongs to another user with a different email. Aborting creation to prevent account collision."
                ))
                return

            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            self.stdout.write(self.style.SUCCESS(
                f"SUPERUSER CREATED — New superuser '{admin_username}' ({admin_email}) created successfully in production database."
            ))
