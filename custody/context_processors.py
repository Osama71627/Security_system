from django.conf import settings

def site_settings(request):
    is_staff = False
    if request.user.is_authenticated:
        is_staff = request.user.is_superuser or request.user.is_staff
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Custody Management System'),
        'SITE_LOGO': getattr(settings, 'SITE_LOGO', 'images/logo.png'),
        'is_staff': is_staff,
    }
