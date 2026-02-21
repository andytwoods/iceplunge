import django.forms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import PlungeLog


class PlungeLogForm(ModelForm):
    # Declared explicitly so Django never auto-inserts a blank "-------" option.
    context = forms.ChoiceField(choices=PlungeLog.Context.choices)
    immersion_depth = forms.ChoiceField(choices=PlungeLog.ImmersionDepth.choices)
    pre_hot_treatment = forms.ChoiceField(
        choices=PlungeLog.PreHotTreatment.choices,
        required=False,
    )
    exercise_timing = forms.ChoiceField(
        choices=PlungeLog.ExerciseTiming.choices,
        required=False,
    )
    exercise_type = forms.ChoiceField(
        choices=PlungeLog.ExerciseType.choices,
        required=False,
    )

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
            "head_submerged",
            "pre_hot_treatment",
            "pre_hot_treatment_minutes",
            "exercise_timing",
            "exercise_type",
            "exercise_minutes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Log Plunge")))

    def clean_pre_hot_treatment(self):
        return self.cleaned_data.get("pre_hot_treatment") or None

    def clean_exercise_timing(self):
        return self.cleaned_data.get("exercise_timing") or None

    def clean_exercise_type(self):
        return self.cleaned_data.get("exercise_type") or None
