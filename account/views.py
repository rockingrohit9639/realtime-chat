from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from .forms import RegistrationForm, AccountAuthenticationForm, AccountUpdateForm
from .models import Account
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.storage import FileSystemStorage
import os
import cv2
import json
import base64
import requests
from django.core import files
from friend.models import FriendList, FriendRequest
from friend.utils import get_request_or_not
from friend.friend_request_status import FriendRequestStatus
from django.contrib import messages
from posts.models import Post, Comment


TEMP_PROFILE_IMAGE_NAME = "temp_profile_image.png"


def register_view(request, *args, **kwargs):
    user = request.user

    if user.is_authenticated:
        return HttpResponse(f"You are already authenticated as {user.username}")

    context = {}
    if request.POST:
        form = RegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email').lower()
            raw_password = form.cleaned_data.get('password1')
            account = authenticate(email=email, password=raw_password)
            login(request, account)
            destination = kwargs.get("next")
            messages.success(request, 'Your account has been successfully created.')
            if destination:
                return redirect(destination)
            return redirect("/")
        else:
            context['registration_form'] = form
    return render(request, 'register.html', context)


def handle_login(request, *args, **kwargs):
    context = {}

    user = request.user
    if user.is_authenticated:
        return redirect("/")

    if request.POST:
        form = AccountAuthenticationForm(request.POST)
        if form.is_valid():
            email = request.POST['email']
            password = request.POST['password']
            user = authenticate(email=email, password=password)
            if user:
                login(request, user)
                messages.success(request, 'You have been logged in successfully.')
                destination = get_redirect_if_exists(request)
                if destination:
                    return redirect(destination)
        else:
            context['login_form'] = form
    return render(request, 'login.html', context)


def handle_logout(request):
    logout(request)
    messages.success(request, 'Successfully logged out.')
    return redirect("/")


def get_redirect_if_exists(request):
    redirect_next = None
    if request.GET:
        if request.GET.get('next'):
            redirect_next = str(request.GET.get('next'))
    return redirect_next


def account_view(request, *args, **kwargs):
    context = {}
    user_id = kwargs.get("user_id")
    try:
        account = Account.objects.get(pk=user_id)
        posts = Post.objects.filter(author=account)
        comments = Comment.objects.all()
    except Exception as e:
        return HttpResponse("Something went wrong.")
    if account:
        context['id'] = account.id
        context['username'] = account.username
        context['email'] = account.email
        context['bio'] = account.bio
        context['profile_image'] = account.profile_image.url
        context['hide_email'] = account.hide_email
        context['posts'] = posts
        context['comments'] = comments

        try:
            friend_list = FriendList.objects.get(user=account)
        except FriendList.DoesNotExist:
            friend_list = FriendList(user=account)
            friend_list.save()
        friends = friend_list.friends.all()
        context['friends'] = friends

        # Define template variables
        is_self = True
        is_friend = False
        request_sent = FriendRequestStatus.NO_FRIEND_REQUEST.value
        friend_requests = None
        user = request.user
        if user.is_authenticated and user != account:
            is_self = False
            if friends.filter(pk=user.id):
                is_friend = True
            else:
                is_friend = False
                # CASE1: Request has been sent from THEM to YOU: FriendRequestStatus.THEM_SENT_TO_YOU
                if get_request_or_not(sender=account, receiver=user):
                    request_sent = FriendRequestStatus.THEM_SENT_YOU.value
                    context['pending_friend_request_id'] = get_request_or_not(sender=account, receiver=user).id
                # CASE2: Request has been sent from YOU to THEM: FriendRequestStatus.YOU_SENT_TO_THEM
                elif get_request_or_not(sender=user, receiver=account):
                    request_sent = FriendRequestStatus.YOU_SENT_THEM.value
                # CASE3: No request sent from YOU or THEM: FriendRequestStatus.NO_REQUEST_SENT
                else:
                    request_sent = FriendRequestStatus.NO_FRIEND_REQUEST.value

        elif not user.is_authenticated:
            is_self = False
        else:
            try:
                friend_requests = FriendRequest.objects.filter(receiver=user, is_active=True)
            except:
                pass

        # Set the template variables to the values
        context['is_self'] = is_self
        context['is_friend'] = is_friend
        context['request_sent'] = request_sent
        context['friend_requests'] = friend_requests
        context['BASE_URL'] = settings.BASE_URL
        return render(request, "account.html", context)


def account_search_view(request, *args, **kwargs):
    context = {}
    if request.method == "GET":
        search_query = request.GET.get("q")
        if len(search_query) > 0:
            search_results = Account.objects.filter(email__icontains=search_query).filter(
                username__icontains=search_query).distinct()
            user = request.user
            accounts = []  # [(account1, True), (account2, False), ...]
            if user.is_authenticated:
                auth_user_friend_list = FriendList.objects.get(user=user)
                for account in search_results:
                    accounts.append((account, auth_user_friend_list.is_mutual_friends(account)))

                context['accounts'] = accounts
            else:
                for account in search_results:
                    accounts.append((account, False))
                context['accounts'] = accounts

    return render(request, "search_results.html", context)


def edit_account_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect("login")

    user_id = kwargs.get("user_id")
    account = Account.objects.get(pk=user_id)

    if account.pk != request.user.pk:
        messages.error(request, 'You are not allowed to edit this profile.')
        return redirect("/")

    context = {}
    if request.POST:
        form = AccountUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account info updated successfully.')
            return redirect("account:account", user_id=account.pk)
        else:
            form = AccountUpdateForm(request.POST, instance=request.user,
                                     initial={
                                         "id": account.pk,
                                         "email": account.email,
                                         "username": account.username,
                                         "bio": account.bio,
                                         "profile_image": account.profile_image,
                                         "hide_email": account.hide_email,
                                     }
                                     )
            context['form'] = form
    else:
        form = AccountUpdateForm(
            initial={
                "id": account.pk,
                "email": account.email,
                "username": account.username,
                "bio": account.bio,
                "profile_image": account.profile_image,
                "hide_email": account.hide_email,
            }
        )
        context['form'] = form
    context['DATA_UPLOAD_MAX_MEMORY_SIZE'] = settings.DATA_UPLOAD_MAX_MEMORY_SIZE
    return render(request, "update_account.html", context)


def edit_bio(request, *args, **kwargs):
    if request.POST:
        user_id = request.POST.get("user_id")
        new_bio = request.POST.get("new_bio")

        user = Account.objects.get(id=user_id)
        user.bio = new_bio
        user.save()

        data = {
             "newBio": new_bio,
        }
        return JsonResponse(data)
    else:
        return HttpResponse("Unexpected request.")


# Saving an image temporarily
def save_temp_profile_image_from_base64String(imageString, user):
    INCORRECT_PADDING_EXCEPTION = "Incorrect padding"
    try:
        if not os.path.exists(settings.TEMP):
            os.mkdir(settings.TEMP)

        if not os.path.exists(settings.TEMP + "/" + str(user.pk)):
            os.mkdir(settings.TEMP + "/" + str(user.pk))

        url = os.path.join(settings.TEMP + "/" + str(user.pk), TEMP_PROFILE_IMAGE_NAME)

        storage = FileSystemStorage(location=url)
        image = base64.b64decode(imageString)
        with storage.open('', 'wb+') as destination:
            destination.write(image)
            destination.close()
        return url
    except Exception as e:
        print("exception: " + str(e))
        # workaround for an issue I found
        if str(e) == INCORRECT_PADDING_EXCEPTION:
            imageString += "=" * ((4 - len(imageString) % 4) % 4)
            return save_temp_profile_image_from_base64String(imageString, user)
    return None


# Cropping an image
def crop_image(request, *args, **kwargs):
    payload = {}
    user = request.user
    if request.POST and user.is_authenticated:
        try:
            imageString = request.POST.get("image")
            url = save_temp_profile_image_from_base64String(imageString, user)
            img = cv2.imread(url)

            cropX = int(float(str(request.POST.get("cropX"))))
            cropY = int(float(str(request.POST.get("cropY"))))
            cropWidth = int(float(str(request.POST.get("cropWidth"))))
            cropHeight = int(float(str(request.POST.get("cropHeight"))))
            if cropX < 0:
                cropX = 0
            if cropY < 0:
                cropY = 0
            crop_img = img[cropY:cropY+cropHeight, cropX:cropX+cropWidth]

            cv2.imwrite(url, crop_img)

            # delete the old image
            user.profile_image.delete()

            # Save the cropped image to user model
            user.profile_image.save("profile_image.png", files.File(open(url, 'rb')))
            user.save()

            payload['result'] = "success"
            payload['cropped_profile_image'] = user.profile_image.url
            # delete temp file
            os.remove(url)

        except Exception as e:
            payload['result'] = "error"
            payload['exception'] = str(e)
    return HttpResponse(json.dumps(payload), content_type="application/json")
