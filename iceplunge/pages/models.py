from django.db import models


class Sponsor(models.Model):
    TIER_INDIVIDUAL = "individual"
    TIER_ORGANISATION = "organisation"
    TIER_CHOICES = [
        (TIER_INDIVIDUAL, "Individual"),
        (TIER_ORGANISATION, "Organisation"),
    ]

    name = models.CharField(max_length=200)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    logo = models.ImageField(upload_to="sponsors/", blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"
