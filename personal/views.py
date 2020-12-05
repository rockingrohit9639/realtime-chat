from django.shortcuts import render
from django.conf import settings


def home(request, *args, **kwargs):
    context = {'debug_mode': settings.DEBUG, 'room_id': "1"}
    return render(request, "personal/index.html", context)
