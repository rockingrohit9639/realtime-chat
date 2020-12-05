import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from public_chat.consumers import PublicChatConsumer
from private_chat.consumers import PrivateChatConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RealtimeChatPlayground.settings")

application = ProtocolTypeRouter({
	"http": get_asgi_application(),
	"websocket": AuthMiddlewareStack(
		URLRouter(
			[
				path('public_chat/<room_id>/', PublicChatConsumer.as_asgi()),
				path('private_chat/<room_id>/', PrivateChatConsumer.as_asgi()),
			]
		)
	)
})