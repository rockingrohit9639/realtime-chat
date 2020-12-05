from django.db import models
from django.conf import settings
from django.utils import timezone


class FriendList(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="friends")

    def __str__(self):
        return self.user.username

    def add_friend(self, account):
        # Adding a friend into friend list
        if not account in self.friends.all():
            self.friends.add(account)
            self.save()

    def remove_friend(self, account):
        # Removing a friend from the friend list
        if account in self.friends.all():
            self.friends.remove(account)

    def unfriend(self, removee):
        # Removing a friend
        remover_friends_list = self
        remover_friends_list.remove_friend(removee)

        friends_list = FriendList.objects.get(user=removee)
        friends_list.remove_friend(self.user)

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

    def __str__(self):
        return self.sender.username

    def accept(self):
        # Accepting the friend request
        receiver_friend_list = FriendList.objects.get(user=self.receiver)
        if receiver_friend_list:
            receiver_friend_list.add_friend(self.sender)

        sender_friend_list = FriendList.objects.get(user=self.sender)
        if sender_friend_list:
            sender_friend_list.add_friend(self.receiver)
            self.is_active = False
            self.save()

    def decline(self):
        # Declining the friend request
        self.is_active = False
        self.save()

    def cancel(self):
        # Cancelling the request from the sender's perspective
        self.is_active = False
        self.save()





