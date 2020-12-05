from django.shortcuts import render


def public_chat_view(request, *args, **kwargs):
    return render(request, 'snippets/public_chat_room.html')
