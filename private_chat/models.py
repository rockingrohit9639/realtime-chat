from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from notification.models import Notification


class PrivateChatRoom(models.Model):
    # Private chat room for individual user
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user2")

    # Users who are currently connected to the socket (Used to keep track of unread messages)
    connected_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="connected_users")

    is_active = models.BooleanField(default=False)

    def connect_user(self, user):
        is_user_added = False
        if not user in self.connected_users.all():
            self.connected_users.add(user)
            is_user_added = True
        return is_user_added

    def disconnect_user(self, user):
        is_user_removed = False
        if user in self.connected_users.all():
            self.connected_users.remove(user)
            is_user_removed = True
        return is_user_removed

    @property
    def group_name(self):
        return f"PrivateChatRoom-{self.id}"


class PrivateChatMessageManager(models.Manager):
    def by_room(self, room):
        qs = PrivateChatMessage.objects.filter(room=room).order_by("-timestamp")
        return qs


class PrivateChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    content = models.TextField(unique=False, blank=False)

    objects = PrivateChatMessageManager()

    def __str__(self):
        return self.content


class UnreadChatRoomMessages(models.Model):
    room = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)

    most_recent_message = models.CharField(max_length=500, blank=True, null=True)
    # Last time messages were read
    reset_timestamp = models.DateTimeField()

    notifications = GenericRelation(Notification)

    def __str__(self):
        return f"Message {str(self.user.username)} has not seen yet."

    def save(self, *args, **kwargs):
        if not self.id:
            self.reset_timestamp = timezone.now()
        return super(UnreadChatRoomMessages, self).save(*args, **kwargs)

    @property
    def get_cname(self):
        # Determine what kind of notification is associated
        return "UnreadChatRoomMessages"

    @property
    def get_other_user(self):
        # Who is other user in the chatroom
        if self.user == self.room.user1:
            return self.room.user2
        else:
            return self.room.user1


@receiver(post_save, sender=PrivateChatRoom)
def create_unread_chatroom_messages_obj(sender, instance, created, **kwargs):
    if created:
        unread_msgs1 = UnreadChatRoomMessages(room=instance, user=instance.user1)
        unread_msgs1.save()

        unread_msgs2 = UnreadChatRoomMessages(room=instance, user=instance.user2)
        unread_msgs2.save()


@receiver(pre_save, sender=UnreadChatRoomMessages)
def increment_unread_messages_count(sender, instance, **kwargs):
    if instance.id is None:
        pass
    else:
        previous = UnreadChatRoomMessages.objects.get(id=instance.id)

        if previous.count < instance.count:
            content_type = ContentType.objects.get_for_model(instance)

            if instance.user == instance.room.user1:
                other_user = instance.room.user2
            else:
                other_user = instance.room.user1

            try:
                notification = Notification.objects.get(target=instance.user, content_type=content_type, object_id=instance.id)
                notification.statement = instance.most_recent_message
                notification.timestamp = timezone.now()
                notification.save()
            except Notification.DoesNotExist:
                instance.notifications.create(
                    target=instance.user,
                    from_user=other_user,
                    redirect_url=f"{settings.BASE_URL}/chat/?room_id={instance.room.id}",
                    # we want to go to the chatroom
                    statement=instance.most_recent_message,
                    content_type=content_type,
                )


@receiver(pre_save, sender=UnreadChatRoomMessages)
def remove_unread_msg_count_notification(sender, instance, **kwargs):
    if instance.id is None: # new object will be created
        pass # create_unread_chatroom_messages_obj will handle this scenario
    else:
        previous = UnreadChatRoomMessages.objects.get(id=instance.id)
        # if count is decremented
        if previous.count > instance.count:
            content_type = ContentType.objects.get_for_model(instance)
            try:
                notification = Notification.objects.get(target=instance.user, content_type=content_type, object_id=instance.id)
                notification.delete()
            except Notification.DoesNotExist:
                pass



