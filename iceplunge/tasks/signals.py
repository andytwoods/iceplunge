"""Signals for the tasks app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from iceplunge.tasks.models import CognitiveSession


@receiver(post_save, sender=CognitiveSession)
def compute_derived_on_start(sender, instance, created, **kwargs):
    """Compute and store derived variables when a session transitions to in_progress."""
    if instance.completion_status != CognitiveSession.CompletionStatus.IN_PROGRESS:
        return
    if instance.started_at is None:
        return
    # Guard against infinite recursion from the update_fields save below.
    if kwargs.get("update_fields") and "derived_variables" in (kwargs["update_fields"] or []):
        return

    from iceplunge.plunges.helpers.session_derived import compute_session_derived

    derived = compute_session_derived(instance.user, instance.started_at)
    CognitiveSession.objects.filter(pk=instance.pk).update(derived_variables=derived)
