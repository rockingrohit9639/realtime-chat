from django.shortcuts import render, redirect, HttpResponse
from django.http import JsonResponse
from .models import Post, Like, Comment
from friend.models import FriendList, FriendRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from account.models import Account


def home(request, *args, **kwargs):
    context = {}
    user = request.user
    if user.is_authenticated:
        posts = Post.objects.all().order_by("-published_date")
        comments = Comment.objects.all().order_by("-timestamp")

        friend_list = FriendList.objects.get(user=user)
        friends = friend_list.friends.all()

        friend_requests = FriendRequest.objects.filter(receiver=user, is_active=True)

        context["posts"] = posts
        context["friends"] = friends
        context["friend_requests"] = friend_requests
        context["comments"] = comments
    else:
        return redirect("login")
    return render(request, "posts/index.html", context)


def new_post(request, *args, **kwargs):
    user = request.user

    if user.is_authenticated:
        if request.POST:
            content = request.POST.get('content')
            feeling = request.POST.get('feeling')
            image = request.FILES.get('file')

            post = Post(author=user, content=content, feeling=feeling, post_image=image)
            post.save()
            messages.success(request, "Post added successfully.")
        else:
            messages.error(request, "Request Denied.")
    else:
        messages.warning(request, "You must be authenticated to add new post.")
    return redirect("/")


@login_required
def like_post(request, *args, **kwargs):
    profile = request.user
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        post_obj = Post.objects.get(id=post_id)

        if profile in post_obj.liked.all():
            post_obj.liked.remove(profile)
            post_obj.save()

            like = Like.objects.get(author=profile, post=post_obj)
            like.delete()

            like_text = "Like"
            icon = "thumb_up"
        else:
            post_obj.liked.add(profile)
            post_obj.save()

            like = Like(author=profile, post=post_obj, value="Unlike")
            like.save()

            like_text = "Unlike"
            icon = "thumb_down"

        # like, created = Like.objects.get_or_create(author=profile, post=post_obj)

        data = {
            'value': like_text,
            'icon': icon,
            'likes': post_obj.liked.all().count()
        }
        return JsonResponse(data, safe=False)
    # return redirect("/")


@login_required
def comment_on_post(request, *args, **kwargs):
    user = request.user
    if request.POST:
        post_id = request.POST.get('post_id')
        comment = request.POST.get('comment')

        post_obj = Post.objects.get(id=post_id)
        new_comment = Comment(author=user, post=post_obj, comment=comment)
        new_comment.save()

        data = {
            'status': "OK",
            'username': user.username,
            'profile_img': user.profile_image.url,
            'comment': comment,
            'post_id': post_id,
        }
        return JsonResponse(data, safe=False)
    else:
        return HttpResponse("Not a valid request.")

