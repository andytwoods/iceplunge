from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import NotificationProfile


class NotificationPreferencesForm(ModelForm):
    class Meta:
        model = NotificationProfile
        fields = ["push_enabled", "morning_window_start", "evening_window_start"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save preferences")))
