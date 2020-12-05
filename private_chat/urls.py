from django.urls import path
from .views import private_chat_room_view, create_or_return_private_chat


app_name = "private_chat"

urlpatterns = [
    path("", private_chat_room_view,name="private chat view"),
    path('create_or_return_private_chat/', create_or_return_private_chat, name='create-or-return-private-chat'),
]