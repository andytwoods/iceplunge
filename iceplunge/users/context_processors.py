from django.conf import settings


def allauth_settings(request):
    """Expose some settings from django-allauth in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
        "GITHUB_SPONSORS_URL": settings.GITHUB_SPONSORS_URL,
        "SPONSOR_CONTACT_EMAIL": settings.SPONSOR_CONTACT_EMAIL,
    }
