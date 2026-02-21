from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import PlungeLog


class PlungeLogForm(ModelForm):
    class Meta:
        model = PlungeLog
        fields = [
            "timestamp",
            "duration_minutes",
            "water_temp_celsius",
            "temp_measured",
            "immersion_depth",
            "context",
            "breathing_technique",
            "perceived_intensity",
            "pre_hot_treatment",
            "pre_hot_treatment_minutes",
            "exercise_timing",
            "exercise_type",
            "exercise_minutes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Strip the blank "-------" choice Django adds for nullable fields rendered as radios
        for field_name in ("pre_hot_treatment", "exercise_timing", "exercise_type"):
            self.fields[field_name].choices = [
                (v, l) for v, l in self.fields[field_name].choices if v != ""
            ]
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Log Plunge")))
