from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import resolve
from django.urls import reverse
from django.urls import Resolver404



CONSENT_EXEMPT_URL_NAMES = {
    "account_login",
    "account_logout",
    "account_signup",
    "account_confirm_email",
    "account_email_verification_sent",
    "account_reset_password",
    "account_reset_password_done",
    "account_reset_password_from_key",
    "account_reset_password_from_key_done",
    "users:consent",
    "users:deletion_complete",
    "users:my_data",  # Article 20 — data portability always accessible
}

CONSENT_EXEMPT_URL_NAMESPACES = {"hijack", "admin", "account", "socialaccount"}


class ConsentRequiredMiddleware:
    """Redirect authenticated users who have not yet consented to the consent page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not self._is_exempt(request):
            profile = getattr(request.user, "consent_profile", None)
            current_version = getattr(settings, "CURRENT_CONSENT_VERSION", "1.0")
            needs_consent = (
                profile is None
                or profile.consented_at is None
                or profile.consent_version != current_version
            )
            if needs_consent:
                if request.method == "GET":
                    # Full-page GET: let through — base.html renders the consent modal overlay
                    pass
                elif request.headers.get("HX-Request"):
                    # HTMX non-GET: force a full page reload so the modal appears
                    response = HttpResponse()
                    response["HX-Redirect"] = "/"
                    return response
                else:
                    return redirect(reverse("users:consent"))
        return self.get_response(request)

    def _is_exempt(self, request) -> bool:
        if request.path.startswith(settings.STATIC_URL):
            return True
        if request.path.startswith(settings.MEDIA_URL):
            return True
        try:
            match = resolve(request.path)
        except Resolver404:
            return False
        full_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
        if full_name in CONSENT_EXEMPT_URL_NAMES:
            return True
        if match.namespace in CONSENT_EXEMPT_URL_NAMESPACES:
            return True
        return False
