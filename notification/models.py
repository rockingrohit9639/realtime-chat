from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(models.Model):
    # To whom the notification is to be sent
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # By whom the notification is coming from
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="from_user")

    redirect_url = models.URLField(max_length=500, null=True, unique=False, blank=True, help_text="Redirect when user "
                                                                                                  "clicks on "
                                                                                                  "notification")
    # What is the notification
    statement = models.CharField(max_length=256, unique=False, blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    # A generic type that can refer to a FriendRequest, Unread Message, or any other type of "Notification"
    # See article: https://simpleisbetterthancomplex.com/tutorial/2016/10/13/how-to-use-generic-relations.html
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return self.statement

    def get_content_object_type(self):
        return str(self.content_object.get_cname)
