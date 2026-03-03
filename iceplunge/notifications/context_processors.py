from django.conf import settings


def onesignal(request):
    return {"ONESIGNAL_APP_ID": settings.ONESIGNAL_APP_ID}
