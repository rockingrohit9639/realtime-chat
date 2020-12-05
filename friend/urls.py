from django.urls import path
from .views import (
    send_friend_request,
    friend_request_view,
    accept_friend_request,
    remove_friend,
    decline_friend_request,
    cancel_friend_request,
    friend_list_view
)

app_name = "friend"

urlpatterns = [
    path('friend-request/', send_friend_request, name='friend request'),
    path('friend-requests/<user_id>/', friend_request_view, name='friend requests'),
    path('accept-friend-requests/<friend_request_id>/', accept_friend_request, name='accept friend requests'),
    path('decline-friend-requests/<friend_request_id>/', decline_friend_request, name='decline friend requests'),
    path('cancel-friend-requests/', cancel_friend_request, name='cancel friend requests'),
    path('remove-friend/', remove_friend, name='remove friend'),
    path('friend-list/<user_id>/', friend_list_view, name="friend list")
]
