from enum import Enum


# Stages of a friend request
class FriendRequestStatus(Enum):
    NO_FRIEND_REQUEST = -1
    THEM_SENT_YOU = 0
    YOU_SENT_THEM = 1

