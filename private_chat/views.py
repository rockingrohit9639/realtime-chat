from django.shortcuts import render, redirect
from django.conf import settings
from itertools import chain
from django.http import HttpResponse
from .models import PrivateChatRoom, PrivateChatMessage
from account.models import Account
from .utils import find_or_create_private_chat
import json
DEBUG = False


def private_chat_room_view(request, *args, **kwargs):
    user = request.user
    room_id = request.GET.get("room_id")

    if not user.is_authenticated:
        return redirect("login")

    context = {}

    if room_id:
        room = PrivateChatRoom.objects.get(pk=room_id)
        context["room"] = room

    # Getting all the rooms for current user
    rooms1 = PrivateChatRoom.objects.filter(user1=user, is_active=True)
    rooms2 = PrivateChatRoom.objects.filter(user2=user, is_active=True)

    # Merging all the rooms together
    rooms = list(chain(rooms1, rooms2))

    # Getting all the messages associated with the friend
    # [{"message": "hey", "friend": "rohit"}, {"message": "You there?", "friend": "lalit"}, ]
    m_and_f = []

    for room in rooms:
        if room.user1 == user:
            friend = room.user2
        else:
            friend = room.user1

        m_and_f.append({
            'message': "",  # blank msg for now (since we have no messages)
            'friend': friend
        })

    print(m_and_f)

    context['m_and_f'] = m_and_f
    context['debug'] = DEBUG
    context['debug_mode'] = settings.DEBUG
    return render(request, "private_chat/room.html", context)


def create_or_return_private_chat(request, *args, **kwargs):
    user1 = request.user

    payload = {}

    if user1.is_authenticated:
        if request.method == "POST":
            user2_id = request.POST.get("user2_id")
            try:
                user2 = Account.objects.get(pk=user2_id)
                chat = find_or_create_private_chat(user1, user2)
                payload['response'] = "Successfully got the chat."
                payload['chatroom_id'] = chat.id
            except Account.DoesNotExist:
                payload['response'] = "Unable to start a chat with that user."
        else:
            payload['response'] = "You can't start a chat if you are not authenticated."
    return HttpResponse(json.dumps(payload), content_type="application/json")



