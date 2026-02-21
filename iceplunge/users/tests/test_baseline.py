from decimal import Decimal

import pytest

from iceplunge.users.forms import BaselineProfileForm
from iceplunge.users.models import BaselineProfile
from iceplunge.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestBaselineProfileBmi:
    def _make_profile(self, user, height_cm, weight_kg):
        return BaselineProfile.objects.create(
            user=user,
            age=30,
            gender="male",
            height_cm=height_cm,
            weight_kg=weight_kg,
            handedness="right",
            plunge_years=Decimal("1.0"),
        )

    def test_bmi_computed_on_create(self):
        user = UserFactory()
        profile = self._make_profile(user, height_cm=Decimal("180.0"), weight_kg=Decimal("80.0"))
        expected = (Decimal("80.0") / (Decimal("180.0") / 100) ** 2).quantize(Decimal("0.01"))
        assert profile.bmi == expected

    def test_bmi_recomputed_on_save(self):
        user = UserFactory()
        profile = self._make_profile(user, height_cm=Decimal("180.0"), weight_kg=Decimal("80.0"))
        profile.weight_kg = Decimal("90.0")
        profile.save()
        expected = (Decimal("90.0") / (Decimal("180.0") / 100) ** 2).quantize(Decimal("0.01"))
        assert profile.bmi == expected

    def test_form_creates_profile_with_correct_bmi(self, client):
        user = UserFactory()
        client.force_login(user)
        form_data = {
            "age": 25,
            "gender": "female",
            "height_cm": "170.0",
            "weight_kg": "65.0",
            "handedness": "right",
            "plunge_years": "2.0",
        }
        form = BaselineProfileForm(data=form_data, instance=None)
        assert form.is_valid(), form.errors
        profile = form.save(commit=False)
        profile.user = user
        profile.save()
        profile.refresh_from_db()
        expected = (Decimal("65.0") / (Decimal("170.0") / 100) ** 2).quantize(Decimal("0.01"))
        assert profile.bmi == expected
