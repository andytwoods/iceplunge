import django.forms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import DailyCovariate
from .models import SessionCovariate
from .models import WeeklyCovariate

SLEEP_QUALITY_CHOICES = [
    (1, _("Poor")),
    (2, _("Fair")),
    (3, _("OK")),
    (4, _("Good")),
    (5, _("Excellent")),
]

GI_SEVERITY_CHOICES = [
    (1, _("None")),
    (2, _("Mild")),
    (3, _("Moderate")),
    (4, _("Significant")),
    (5, _("Severe")),
]

GI_SYMPTOM_CHOICES = [
    ("bloating", _("Bloating")),
    ("cramps", _("Cramps")),
    ("nausea", _("Nausea")),
    ("diarrhea", _("Diarrhea")),
    ("constipation", _("Constipation")),
    ("reflux", _("Reflux / heartburn")),
]


class DailyCovariateForm(ModelForm):
    # Declared explicitly so Django never auto-inserts a blank "-------" option.
    sleep_quality = forms.TypedChoiceField(
        choices=SLEEP_QUALITY_CHOICES,
        coerce=int,
        required=False,
        empty_value=None,
    )

    class Meta:
        model = DailyCovariate
        fields = ["sleep_duration_hours", "sleep_quality", "alcohol_last_24h", "exercise_today"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save")))


class WeeklyCovariateForm(ModelForm):
    # Declared explicitly so Django never auto-inserts a blank "-------" option.
    gi_severity = forms.TypedChoiceField(
        choices=GI_SEVERITY_CHOICES,
        coerce=int,
        required=False,
        empty_value=None,
    )
    gi_symptoms = forms.MultipleChoiceField(
        choices=GI_SYMPTOM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = WeeklyCovariate
        fields = ["gi_severity", "gi_symptoms", "illness_status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["gi_symptoms"] = self.instance.gi_symptoms or []
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save")))

    def clean_gi_symptoms(self):
        return self.cleaned_data.get("gi_symptoms") or []


class SessionCovariateForm(ModelForm):
    class Meta:
        model = SessionCovariate
        fields = ["caffeine_since_last_session", "minutes_since_last_meal", "cold_hands", "wet_hands"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Continue")))
