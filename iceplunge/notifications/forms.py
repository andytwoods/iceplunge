from crispy_forms.helper import FormHelper
from crispy_bulma.layout import Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import NotificationProfile


class NotificationPreferencesForm(ModelForm):
    class Meta:
        model = NotificationProfile
        fields = ["push_enabled", "notifications_per_day", "window_start", "window_end"]
        labels = {
            "push_enabled": _("Enable push notifications"),
            "notifications_per_day": _("Alerts per day"),
            "window_start": _("Window start time"),
            "window_end": _("Window end time"),
        }
        help_texts = {
            "notifications_per_day": _(
                "How many reminders you would like each day. Set to 0 to disable scheduled alerts."
            ),
            "window_start": _("Earliest time you want to receive an alert."),
            "window_end": _("Latest time you want to receive an alert."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save preferences"), css_class="is-primary is-fullwidth"))
