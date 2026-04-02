from django.conf import settings


def allauth_settings(request):
    """Expose some settings from django-allauth in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
        "GITHUB_SPONSORS_URL": settings.GITHUB_SPONSORS_URL,
        "GITHUB_REPO_URL": settings.GITHUB_REPO_URL,
        "SPONSOR_CONTACT_EMAIL": settings.SPONSOR_CONTACT_EMAIL,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
    }


def consent_modal(request):
    """Inject consent modal flags so base.html can show the overlay when needed."""
    if not request.user.is_authenticated:
        return {"show_consent_modal": False, "consent_version_outdated": False}

    profile = getattr(request.user, "consent_profile", None)
    current_version = getattr(settings, "CURRENT_CONSENT_VERSION", "1.0")

    previously_consented = profile is not None and profile.consented_at is not None
    version_outdated = previously_consented and profile.consent_version != current_version
    needs_consent = (
        profile is None
        or profile.consented_at is None
        or profile.consent_version != current_version
    )
    return {
        "show_consent_modal": needs_consent,
        "consent_version_outdated": version_outdated,
    }
