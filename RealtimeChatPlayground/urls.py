from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from account.views import (
    register_view,
    handle_login,
    handle_logout,
    account_search_view,
)


urlpatterns = [
    path('account/', include("account.urls")),
    path('admin/', admin.site.urls),
    path('chat/', include("private_chat.urls", namespace="chat")),
    path('friend/', include("friend.urls", namespace="friend")),
    path('login/', handle_login, name="login"),
    path('logout/', handle_logout, name="logout"),
    path('register/', register_view, name="register"),
    path('search/', account_search_view, name="search"),
    path('', include('personal.urls')),


    # Password reset and change urls
    path('password_change/done/',
         auth_views.PasswordChangeDoneView.as_view(template_name='password_reset/password_change_done.html'),
         name='password_change_done'),

    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='password_reset/password_change.html'),
         name='password_change'),

    path('password_reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_done.html'),
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),

    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_complete.html'),
         name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
