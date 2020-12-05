from django.db import models
from django.conf import settings


class PrivateChatRoom(models.Model):
    # Private chat room for individual user
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user2")

    is_active = models.BooleanField(default=False)

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
