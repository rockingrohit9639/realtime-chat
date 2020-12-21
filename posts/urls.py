from django.urls import path
from .views import (home,
                    new_post,
                    like_post,
                    comment_on_post,
                    delete_post,
                    edit_post,
                    )

app_name = "posts"

urlpatterns = [
    path("", home, name="Public Chat Room"),
    path("add/", new_post, name="Add new post"),
    path("like/", like_post, name="Like post"),
    path("add-comment/", comment_on_post, name="Comment on post"),
    path("delete-post/<post_id>", delete_post, name="Delete post"),
    path("edit-post/", edit_post, name="Edit post"),
]