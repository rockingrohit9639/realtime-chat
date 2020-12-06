from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from notification.models import Notification
from private_chat.utils import find_or_create_private_chat
from django.db.models.signals import post_save
from django.dispatch import receiver


# Creating a friend list for each user
class FriendList(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="friends")

    notifications = GenericRelation(Notification)

    def __str__(self):
        return self.user.username

    def add_friend(self, account):
        # Adding a friend into friend list
        if not account in self.friends.all():
            self.friends.add(account)
            self.save()

            content_type = ContentType.objects.get_for_model(self)

            self.notifications.create(
                target=self.user,
                from_user=account,
                redirect_url=f"{settings.BASE_URL}/account/{account.pk}/",
                statement=f"You are now friend with {account.user}",
                content_type=content_type
            )
            self.save()

            # Creating a private chat room when two users become friends
            chat = find_or_create_private_chat(self.user, account)
            if not chat.is_active:
                chat.is_active = True
                chat.save()

    def remove_friend(self, account):
        # Removing a friend from the friend list
        if account in self.friends.all():
            self.friends.remove(account)

            # Deactivating the private chat room when two users are no longer friends
            chat = find_or_create_private_chat(self.user, account)
            if chat.is_active:
                chat.is_active = False
                chat.save()

    def unfriend(self, removee):
        # Removing a friend
        remover_friends_list = self
        remover_friends_list.remove_friend(removee)

        friends_list = FriendList.objects.get(user=removee)
        friends_list.remove_friend(self.user)

        content_type = ContentType.objects.get_for_model(self)

        # Notification for removee
        friends_list.notifications.create(
            target=removee,
            from_user=self.user,
            redirect_url=f"{settings.BASE_URL}/account/{self.user.pk}/",
            statement=f"You are no longer friends with {self.user.username}.",
            content_type=content_type,
        )

        # Notification for remover
        self.notifications.create(
            target=self.user,
            from_user=removee,
            redirect_url=f"{settings.BASE_URL}/account/{removee.pk}/",
            statement=f"You are no longer friends with {removee.username}.",
            content_type=content_type,
        )

    @property
    def get_cname(self):
        """
        For determining what kind of object is associated with a Notification
        """
        return "FriendList"

    def is_mutual_friends(self, friend):
        # Getting the result if the friends are mutual
        if friend in self.friends.all():
            return True
        return False


class FriendRequest(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sender")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receiver")
    is_active = models.BooleanField(blank=True, null=False, default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    notifications = GenericRelation(Notification)

    def __str__(self):
        return self.sender.username

    def accept(self):
        # Accepting the friend request
        receiver_friend_list = FriendList.objects.get(user=self.receiver)
        if receiver_friend_list:
            content_type = ContentType.objects.get_for_model(self)

            # Updating notification for RECEIVER
            receiver_notification = Notification.objects.get(target=self.receiver, content_type=content_type,
                                                             object_id=self.id)
            receiver_notification.is_active = False
            receiver_notification.redirect_url = f"{settings.BASE_URL}/account/{self.sender.pk}/"
            receiver_notification.statement = f"You accepted {self.sender.username}'s friend request."
            receiver_notification.timestamp = timezone.now()
            receiver_notification.save()
            receiver_friend_list.add_friend(self.sender)

            sender_friend_list = FriendList.objects.get(user=self.sender)
            if sender_friend_list:
                # Create notification for SENDER
                self.notifications.create(
                    target=self.sender,
                    from_user=self.receiver,
                    redirect_url=f"{settings.BASE_URL}/account/{self.receiver.pk}/",
                    statement=f"{self.receiver.username} accepted your friend request.",
                    content_type=content_type,
                )

                sender_friend_list.add_friend(self.receiver)
                self.is_active = False
                self.save()
            return receiver_notification

    def decline(self):
        # Declining the friend request
        self.is_active = False
        self.save()

        content_type = ContentType.objects.get_for_model(self)

        # Update notification for RECEIVER
        notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
        notification.is_active = False
        notification.redirect_url = f"{settings.BASE_URL}/account/{self.sender.pk}/"
        notification.statement = f"You declined {self.sender}'s friend request."
        notification.from_user = self.sender
        notification.timestamp = timezone.now()
        notification.save()

        # Create notification for SENDER
        self.notifications.create(
            target=self.sender,
            statement=f"{self.receiver.username} declined your friend request.",
            from_user=self.receiver,
            redirect_url=f"{settings.BASE_URL}/account/{self.receiver.pk}/",
            content_type=content_type,
        )

        return notification

    def cancel(self):
        # Cancelling the request from the sender's perspective
        self.is_active = False
        self.save()

        content_type = ContentType.objects.get_for_model(self)

        # Create notification for SENDER
        self.notifications.create(
            target=self.sender,
            statement=f"You cancelled the friend request to {self.receiver.username}.",
            from_user=self.receiver,
            redirect_url=f"{settings.BASE_URL}/account/{self.receiver.pk}/",
            content_type=content_type,
        )

        notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
        notification.statement = f"{self.sender.username} cancelled the friend request sent to you."
        # notification.timestamp = timezone.now()
        notification.read = False
        notification.save()

    @property
    def get_cname(self):
        """
        For determining what kind of object is associated with a Notification
        """
        return "FriendRequest"


@receiver(post_save, sender=FriendRequest)
def create_notification(sender, instance, created, **kwargs):
    if created:
        instance.notifications.create(
            target=instance.receiver,
            from_user=instance.sender,
            redirect_url=f"{settings.BASE_URL}/account/{instance.sender.pk}/",
            statement=f"{instance.sender.username} sent you a friend request.",
            content_type=instance,
        )




