
from decimal import Decimal
from typing import ClassVar
from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import EmailField
from django.db.models import Model
from django.db.models import OneToOneField
from django.db.models import PositiveSmallIntegerField
from django.db.models import TextChoices
from django.db.models import UUIDField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for iceplunge.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    # Stable pseudonymised identifier used in all research data exports (never PII)
    pseudonymised_id = UUIDField(default=uuid4, unique=True, editable=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class ConsentProfile(Model):
    user = OneToOneField(User, on_delete=CASCADE, related_name="consent_profile")
    consented_at = DateTimeField(null=True, blank=True)
    consent_version = CharField(max_length=20, default="1.0")

    def __str__(self) -> str:
        return f"Consent: {self.user} ({'given' if self.consented_at else 'pending'})"


class BaselineProfile(Model):
    class Handedness(TextChoices):
        LEFT = "left", _("Left")
        RIGHT = "right", _("Right")
        AMBIDEXTROUS = "ambidextrous", _("Ambidextrous")

    user = OneToOneField(User, on_delete=CASCADE, related_name="baseline_profile")
    age = PositiveSmallIntegerField()
    gender = CharField(max_length=50)
    height_cm = DecimalField(max_digits=5, decimal_places=1)
    weight_kg = DecimalField(max_digits=5, decimal_places=1)
    bmi = DecimalField(max_digits=5, decimal_places=2, editable=False)
    handedness = CharField(max_length=20, choices=Handedness.choices)
    plunge_years = DecimalField(max_digits=4, decimal_places=1)

    def save(self, *args, **kwargs):
        height_m = Decimal(str(self.height_cm)) / Decimal("100")
        self.bmi = (Decimal(str(self.weight_kg)) / (height_m ** 2)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Baseline: {self.user}"
