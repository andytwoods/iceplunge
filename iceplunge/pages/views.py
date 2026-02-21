from django.views.generic import TemplateView

from .models import Sponsor


class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sponsors = Sponsor.objects.filter(is_active=True)
        context["org_sponsors"] = sponsors.filter(tier=Sponsor.TIER_ORGANISATION)
        context["individual_sponsors"] = sponsors.filter(tier=Sponsor.TIER_INDIVIDUAL)
        return context
