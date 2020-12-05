from enum import Enum


class FriendRequestStatus(Enum):
    NO_FRIEND_REQUEST = -1
    THEM_SENT_YOU = 0
    YOU_SENT_THEM = 1

