from django.urls import path
from .views import account_view, edit_account_view, crop_image

app_name = "account"

urlpatterns = [
    path("<user_id>/", account_view, name="account"),
    path("<user_id>/edit/", edit_account_view, name="edit"),
    path("<user_id>/edit/cropImg/", crop_image, name="crop"),

]