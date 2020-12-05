from django.db import models
from django.conf import settings
from account.models import Account


class PublicChatRoom(models.Model):
    title = models.CharField(max_length=255, unique=True, blank=False)
    users = models.ManyToManyField(Account, blank=True, help_text="Users who are connected")

    def __str__(self):
        return self.title

    def connect_user(self, user):
        is_user_added = False
        if user not in self.users.all():
            self.users.add(user)
            is_user_added = True
        elif user in self.users.all():
            is_user_added = True
        return is_user_added

    def disconnect_user(self, user):
        is_user_removed = False
        if user in self.users.all():
            is_user_removed = True
            self.users.remove(user)
            self.save()
        return is_user_removed

    @property
    def group_name(self):
        return f"PublicChatRoom-{self.id}"


class PublicChatMessageManager(models.Manager):
    def by_room(self, room):
        qs = PublicChatMessage.objects.filter(room=room).order_by("-timestamp")
        return qs


class PublicChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(PublicChatRoom, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    content = models.TextField(unique=False, blank=False)

    objects = PublicChatMessageManager()

    def __str__(self):
        return self.content


