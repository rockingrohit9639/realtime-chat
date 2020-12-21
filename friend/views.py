from django.shortcuts import render, redirect
from django.http import HttpResponse
import json
from account.models import Account
from .models import FriendRequest, FriendList


def send_friend_request(request, *args, **kwargs):
    user = request.user
    payload = {}
    if request.method == "POST" and user.is_authenticated:
        user_id = request.POST.get("user_id")
        if user_id:
            receiver = Account.objects.get(pk=user_id)
            try:
                # Get any friend requests (active and not-active)
                friend_requests = FriendRequest.objects.filter(sender=user, receiver=receiver)
                # find if any of them are active (pending)
                try:
                    for request in friend_requests:
                        if request.is_active:
                            raise Exception("You already sent them a friend request.")
                    # If none are active create a new friend request
                    friend_request = FriendRequest(sender=user, receiver=receiver)
                    friend_request.save()
                    payload['response'] = "Friend request sent."
                except Exception as e:
                    payload['response'] = str(e)
            except FriendRequest.DoesNotExist:
                # There are no friend requests so create one.
                friend_request = FriendRequest(sender=user, receiver=receiver)
                friend_request.save()
                payload['response'] = "Friend request sent."

            if payload['response'] is None:
                payload['response'] = "Something went wrong."
        else:
            payload['response'] = "Unable to sent a friend request."
    else:
        payload['response'] = "You must be authenticated to send a friend request."
    return HttpResponse(json.dumps(payload), content_type="application/json")


def accept_friend_request(request, *args, **kwargs):
    user = request.user
    payload = {}

    if request.method == "POST" and user.is_authenticated:
        friend_req_id = kwargs.get("friend_request_id")
        print(friend_req_id)
        if friend_req_id:
            friend_request = FriendRequest.objects.get(pk=friend_req_id)
            if friend_request.receiver == user:
                if friend_request:
                    friend_request.accept()
                    payload['response'] = "Friend request accepted."
                else:
                    payload['response'] = "Something went wrong."
            else:
                payload['response'] = "You can not accept this friend request."
        else:
            payload['response'] = "Unable to accept this friend request."
    else:
        payload['response'] = "You must be authenticated to accept a friend request."
    return HttpResponse(json.dumps(payload), content_type="application/json")


def remove_friend(request, *args, **kwargs):
    user = request.user
    payload = {}

    if request.method == "POST" and user.is_authenticated:
        user_id = request.POST.get('receiver_user_id')
        if user_id:
            try:
                removee = Account.objects.get(pk=user_id)
                friend_list = FriendList.objects.get(user=user)
                friend_list.unfriend(removee)
                payload['response'] = "success"
            except Exception as e:
                payload['response'] = f"Something went wrong {str(e)}"
        else:
            payload['response'] = "Unable to remove friend"
    else:
        payload['response'] = "You must be authenticated."
    return HttpResponse(json.dumps(payload), content_type="application/json")


def decline_friend_request(request, *args, **kwargs):
    user = request.user
    payload = {}

    if request.method == "GET" and user.is_authenticated:
        friend_request_id = kwargs.get('friend_request_id')

        if friend_request_id:
            friend_request = FriendRequest.objects.get(pk=friend_request_id)

            if friend_request.receiver == user:
                if friend_request:
                    friend_request.decline()
                    payload['response'] = "success"
                else:
                    payload['response'] = "something went wrong."
            else:
                payload['response'] = "That is not your fried request to decline."
        else:
            payload['response'] = "Unable to decline the request."
    else:
        payload['response'] = "You are not allowed here."
    return HttpResponse(json.dumps(payload), content_type="application/json")


def cancel_friend_request(request, *args, **kwargs):
    user = request.user
    payload = {}

    if request.method == "POST" and user.is_authenticated:
        user_id = request.POST.get('receiver_user_id')
        friend_requests = None
        if user_id:
            receiver = Account.objects.get(pk=user_id)

            try:
                friend_requests = FriendRequest.objects.filter(sender=user, receiver=receiver, is_active=True)
            except Exception as e:
                payload['response'] = "Nothing to cancel. " + str(e)

            if len(friend_requests) > 1:
                for req in friend_requests:
                    req.cancel()
                payload['response'] = "success"
            else:
                friend_requests.first().cancel()
                payload['response'] = "success"
        else:
            payload['response'] = "Unable to cancel this request."
    else:
        payload['response'] = "You are not allowed here."
    return HttpResponse(json.dumps(payload), content_type="application/json")


def friend_list_view(request, *args, **kwargs):
    context = {}
    user = request.user

    if user.is_authenticated:
        user_id = kwargs.get('user_id')
        if user_id:
            try:
                this_user = Account.objects.get(pk=user_id)
                context['this_user'] = this_user
            except Account.DoesNotExist:
                return HttpResponse("Account Does Not Exists")
            try:
                friend_list = FriendList.objects.get(user=this_user)
            except FriendList.DoesNotExist:
                return HttpResponse(f"Could not find friend list for {this_user.username}")

            if user != this_user:
                if user not in friend_list.friends.all():
                    return HttpResponse("You must be friends to check the friend list.")

            friends = []
            auth_user_friend_list = FriendList.objects.get(user=user)
            for friend in friend_list.friends.all():
                friends.append((friend, auth_user_friend_list.is_mutual_friends(friend)))
            context['friends'] = friends
    else:
        return HttpResponse("You must be authenticated.")
    return render(request, "friend/friend_list.html", context)


def friend_request_view(request, *args, **kwargs):
    context = {}
    user = request.user

    if user.is_authenticated:
        user_id = kwargs.get("user_id")
        account = Account.objects.get(pk=user_id)
        if account == user:
            friend_requests = FriendRequest.objects.filter(receiver=account, is_active=True)
            context['friend_requests'] = friend_requests
        else:
            HttpResponse("You can not view other user's friend requests.")
    else:
        return redirect("login")
    return render(request, "friend/friend_requests.html", context)