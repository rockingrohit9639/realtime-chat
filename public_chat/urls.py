from django.urls import path
from .views import public_chat_view

urlpatterns = [
    path("", public_chat_view, name="Public Chat Room")
]