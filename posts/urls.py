from django.urls import path
from .views import home, new_post, like_post, comment_on_post

urlpatterns = [
    path("", home, name="Public Chat Room"),
    path("add/", new_post, name="Add new post"),
    path("like/", like_post, name="Like post"),
    path("add-comment/", comment_on_post, name="Comment on post"),
]