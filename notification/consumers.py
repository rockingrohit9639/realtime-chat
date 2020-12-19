from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.paginator import Paginator
from django.core.serializers import serialize
from channels.db import database_sync_to_async
from django.contrib.contenttypes.models import ContentType
import json
from datetime import datetime
from private_chat.exceptions import ClientError
from friend.models import FriendList, FriendRequest
from .models import Notification
from .utils import LazyNotificationEncoder
from private_chat.models import UnreadChatRoomMessages
from private_chat.utils import calculate_timestamp
from posts.models import Like, Comment
from .constants import *


class NotificationConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.accept()

    async def disconnect(self, code):
        print("Notification Consumer : disconnect")

    async def receive_json(self, content, **kwargs):
        command = content.get("command", None)

        try:
            if command == "get_general_notifications":
                payload = await get_general_notifications(self.scope['user'], content.get("page_number", None))
                if payload is None:
                    await self.general_pagination_exhausted()
                else:
                    payload = json.loads(payload)
                    await self.send_general_notification_payload(payload['notifications'], payload['new_page_number'])

            elif command == "accept_friend_request":
                notification_id = content['notification_id']
                payload = await accept_friend_request(self.scope['user'], notification_id)
                if payload is None:
                    raise ClientError("UNKNOWN_ERROR", "Something went wrong.")
                else:
                    payload = json.dumps(payload)
                    await self.send_updated_friend_request_notification(payload['notification'])

            elif command == "decline_friend_request":
                notification_id = content['notification_id']
                payload = await decline_friend_request(self.scope['user'], notification_id)
                if payload is None:
                    raise ClientError("UNKNOWN_ERROR", "Something went wrong. Try refreshing the browser.")
                else:
                    payload = json.loads(payload)
                    await self.send_updated_friend_request_notification(payload['notification'])

            elif command == "refresh_general_notifications":
                payload = await refresh_general_notifications(self.scope["user"], content['oldest_timestamp'], content['newest_timestamp'])
                if payload is None:
                    raise ClientError("UNKNOWN_ERROR", "Something went wrong. Try refreshing the browser.")
                else:
                    payload = json.loads(payload)
                    await self.send_general_refreshed_notifications_payload(payload['notifications'])

            elif command == "get_new_general_notifications":
                payload = await get_new_general_notifications(self.scope["user"], content.get("newest_timestamp", None))
                if payload is not None:
                    payload = json.loads(payload)
                    await self.send_new_general_notifications_payload(payload['notifications'])

            elif command == "get_unread_general_notifications_count":
                payload = await get_unread_general_notification_count(self.scope["user"])
                if payload is not None:
                    payload = json.loads(payload)
                    await self.send_unread_general_notification_count(payload['count'])

            elif command == "mark_notifications_read":
                await mark_notifications_read(self.scope["user"])

            elif command == "get_chat_notifications":
                payload = await get_chat_notifications(self.scope["user"], content.get("page_number", None))
                if payload is None:
                    pass
                else:
                    payload = json.loads(payload)
                    await self.send_chat_notifications_payload(payload['notifications'], payload['new_page_number'])

            elif command == "get_new_chat_notifications":
                payload = await get_new_chat_notifications(self.scope["user"], content.get("newest_timestamp", None))
                if payload is not None:
                    payload = json.loads(payload)
                    await self.send_new_chat_notifications_payload(payload['notifications'])

            elif command == "get_unread_chat_notifications_count":
                try:
                    payload = await get_unread_chat_notification_count(self.scope["user"])
                    if payload is not None:
                        payload = json.loads(payload)
                        await self.send_unread_chat_notification_count(payload['count'])
                except Exception as e:
                    print("UNREAD CHAT MESSAGE COUNT EXCEPTION: " + str(e))
                    pass

            # elif command == "get_like_notifications":
            #     payload = await get_likes_notifications(self.scope['user'])
            #     if payload is None:
            #         print("No like notifications")
            #     else:
            #         payload = json.loads(payload)
            #         await self.send_like_notification_payload(payload['notifications'])

        except ClientError as e:
            print("Exception : ", str(e))

    async def display_progress_bar(self, is_displayed):
        await self.send_json(
            {
                "progress_bar": is_displayed,
            },
        )

    async def send_general_notification_payload(self, notifications, new_page_number):
        await self.send_json({
            "general_msg_type": GENERAL_MSG_TYPE_NOTIFICATIONS_PAYLOAD,
            "notifications": notifications,
            "new_page_number": new_page_number
        })

    async def send_updated_friend_request_notification(self, notification):
        await self.send_json({
            "general_msg_type": GENERAL_MSG_TYPE_UPDATED_NOTIFICATION,
            "notification": notification,
        })

    async def general_pagination_exhausted(self):
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_PAGINATION_EXHAUSTED,
            },
        )

    async def send_general_refreshed_notifications_payload(self, notifications):
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_NOTIFICATIONS_REFRESH_PAYLOAD,
                "notifications": notifications,
            },
        )

    async def send_new_general_notifications_payload(self, notifications):
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_GET_NEW_GENERAL_NOTIFICATIONS,
                "notifications": notifications,
            },
        )

    async def send_unread_general_notification_count(self, count):
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_GET_UNREAD_NOTIFICATIONS_COUNT,
                "count": count,
            },
        )

    async def send_chat_notifications_payload(self, notifications, new_page_number):
        await self.send_json(
            {
                "chat_msg_type": CHAT_MSG_TYPE_NOTIFICATIONS_PAYLOAD,
                "notifications": notifications,
                "new_page_number": new_page_number,
            },
        )

    async def send_new_chat_notifications_payload(self, notifications):
        await self.send_json(
            {
                "chat_msg_type": CHAT_MSG_TYPE_GET_NEW_NOTIFICATIONS,
                "notifications": notifications,
            },
        )

    async def send_unread_chat_notification_count(self, count):
        await self.send_json(
            {
                "chat_msg_type": CHAT_MSG_TYPE_GET_UNREAD_NOTIFICATIONS_COUNT,
                "count": count,
            },
        )

    async def send_like_notification_payload(self, notifications):
        await self.send_json({
            "type": "like",
            "notifications": notifications
        })


@database_sync_to_async
def get_general_notifications(user, page_number):
    if user.is_authenticated:
        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        like_ct = ContentType.objects.get_for_model(Like)
        comment_ct = ContentType.objects.get_for_model(Comment)

        notifications = Notification.objects.filter(target=user, content_type__in=[friend_list_ct, friend_request_ct, like_ct, comment_ct]).order_by("-timestamp")
        p = Paginator(notifications, DEFAULT_NOTIFICATION_PAGE_SIZE)

        payload = {}
        if len(notifications) > 0:
            if int(page_number) <= p.num_pages:
                s = LazyNotificationEncoder()
                serialized_notifications = s.serialize(p.page(page_number).object_list)
                payload['notifications'] = serialized_notifications
                new_page_number = int(page_number) + 1
                payload['new_page_number'] = new_page_number
        else:
            return None
    else:
        raise ClientError("AUTH_ERROR", "User must be authenticated to get notifications")
    return json.dumps(payload)


@database_sync_to_async
def accept_friend_request(user, notification_id):
    payload = {}

    if user.is_authenticated:
        try:
            notification = Notification.objects.get(pk=notification_id)
            friend_request = notification.content_object

            if friend_request.receiver == user:
                # accept the request and get the updated notification
                updated_notification = friend_request.accept()

                # return the notification associated with this FriendRequest
                s = LazyNotificationEncoder()
                payload['notification'] = s.serialize([updated_notification])[0]
                return json.dumps(payload)
        except Notification.DoesNotExist:
            raise ClientError("UNKNOWN_ERROR", "An error occurred while getting the notification. Try refreshing.")
    return None


@database_sync_to_async
def decline_friend_request(user, notification_id):
    payload = {}

    if user.is_authenticated:
        try:
            notification = Notification.objects.get(pk=notification_id)
            friend_request = notification.content_object

            if friend_request.receiver == user:
                updated_notification = friend_request.decline()

                s = LazyNotificationEncoder()
                payload['notification'] = s.serialize([updated_notification])[0]
                json.dumps(payload)
        except Notification.DoesNotExist:
            raise ClientError("UNKNOWN_ERROR", "An error occurred with that notification. Try refreshing the browser.")
        return None


@database_sync_to_async
def refresh_general_notifications(user, oldest_timestamp, newest_timestamp):
    payload = {}
    if user.is_authenticated:
        newest_timestamp = datetime.now()

        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)

        like_ct = ContentType.objects.get_for_model(Like)
        comment_ct = ContentType.objects.get_for_model(Comment)

        notifications = Notification.objects.filter(target=user, content_type__in=[friend_request_ct, friend_list_ct, like_ct, comment_ct], timestamp__gte=oldest_timestamp, timestamp__lte=newest_timestamp).order_by('-timestamp')

        s = LazyNotificationEncoder()
        payload['notifications'] = s.serialize(notifications)
    else:
        raise ClientError("AUTH_ERROR", "User must be authenticated to get notifications.")

    return json.dumps(payload)


@database_sync_to_async
def get_new_general_notifications(user, newest_timestamp):
    payload = {}

    if user .is_authenticated:
        newest_timestamp = datetime.now()

        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        like_ct = ContentType.objects.get_for_model(Like)
        comment_ct = ContentType.objects.get_for_model(Comment)

        notifications = Notification.objects.filter(target=user, content_type__in=[friend_request_ct, friend_list_ct, like_ct, comment_ct], timestamp__lte=newest_timestamp, is_read=False).order_by('-timestamp')

        s = LazyNotificationEncoder()

        payload['notifications'] = s.serialize(notifications)
    else:
        raise ClientError("AUTH_ERROR", "User must be authenticated.")
    return json.dumps(payload)


@database_sync_to_async
def get_unread_general_notification_count(user):
    payload = {}
    if user.is_authenticated:
        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        like_ct = ContentType.objects.get_for_model(Like)
        comment_ct = ContentType.objects.get_for_model(Comment)

        notifications = Notification.objects.filter(target=user, content_type__in=[friend_request_ct, friend_list_ct, like_ct, comment_ct])

        unread_count = 0
        if notifications:
            for notification in notifications.all():
                if not notification.is_read:
                    unread_count = unread_count + 1
        payload['count'] = unread_count
        return json.dumps(payload)
    else:
        raise ClientError("AUTH_ERROR", "User must be authentic ated to get notifications.")
    return None


@database_sync_to_async
def mark_notifications_read(user):
    if user.is_authenticated:
        notifications = Notification.objects.filter(target=user)
        if notifications:
            for notification in notifications.all():
                notification.is_read = True
                notification.save()
    return


@database_sync_to_async
def get_chat_notifications(user, page_number):
    if user.is_authenticated:
        chatmessage_ct = ContentType.objects.get_for_model(UnreadChatRoomMessages)
        notifications = Notification.objects.filter(target=user, content_type=chatmessage_ct).order_by('-timestamp')
        p = Paginator(notifications, DEFAULT_NOTIFICATION_PAGE_SIZE)

        payload = {}
        if len(notifications) > 0:
            if int(page_number) <= p.num_pages:
                s = LazyNotificationEncoder()
                serialized_notifications = s.serialize(p.page(page_number).object_list)
                payload['notifications'] = serialized_notifications
                new_page_number = int(page_number) + 1
                payload['new_page_number'] = new_page_number
        else:
            return None
    else:
        raise ClientError("AUTH_ERROR", "User must be authenticated to get notifications.")
    return json.dumps(payload)


@database_sync_to_async
def get_new_chat_notifications(user, newest_timestamp):
    payload = {}
    if user.is_authenticated:

        timestamp = datetime.now()

        chatmessage_ct = ContentType.objects.get_for_model(UnreadChatRoomMessages)
        notifications = Notification.objects.filter(target=user, content_type__in=[chatmessage_ct], timestamp__gt=timestamp).order_by('-timestamp')
        s = LazyNotificationEncoder()
        payload['notifications'] = s.serialize(notifications)
    else:
        raise ClientError("AUTH_ERROR", "User must be authenticated to get notifications.")

    return json.dumps(payload)


@database_sync_to_async
def get_unread_chat_notification_count(user):
    payload = {}
    if user.is_authenticated:
        chatmessage_ct = ContentType.objects.get_for_model(UnreadChatRoomMessages)
        notifications = Notification.objects.filter(target=user, content_type__in=[chatmessage_ct])

        unread_count = 0
        if notifications:
            unread_count = len(notifications.all())
        payload['count'] = unread_count
        return json.dumps(payload)
    else:
        raise ClientError("AUTH_ERROR", "User must be authenticated to get notifications.")
    return None