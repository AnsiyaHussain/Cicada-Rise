import os
from django.shortcuts import redirect
from django.contrib import messages

class StrictAdminAccessMiddleware:
    """
    Strict security middleware enforcing that /admin/ and /dashboard/ routes
    can ONLY be accessed by an authenticated user with is_staff=True, is_superuser=True,
    and matching approved admin email configured in DJANGO_SUPERUSER_EMAIL.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith('/admin/') or path.startswith('/dashboard/'):
            if path == '/admin/login/':
                return self.get_response(request)

            if not request.user.is_authenticated:
                messages.error(request, "Access Denied: Authentication required.")
                return redirect('login')

            approved_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip().lower()

            # Fail closed if DJANGO_SUPERUSER_EMAIL is not configured
            if not approved_email:
                messages.error(request, "Access Denied: Admin configuration missing.")
                return redirect('home')

            user_email = (request.user.email or '').strip().lower()

            is_approved = (
                request.user.is_staff and 
                request.user.is_superuser and 
                user_email == approved_email
            )

            if not is_approved:
                messages.error(request, "Access Denied: Administrator credentials required.")
                return redirect('home')

        return self.get_response(request)
