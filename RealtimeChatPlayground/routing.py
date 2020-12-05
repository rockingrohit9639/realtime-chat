import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from public_chat.consumers import PublicChatConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RealtimeChatPlayground.settings")

application = ProtocolTypeRouter({
	"http": get_asgi_application(),
	"websocket": AuthMiddlewareStack(
		URLRouter(
			[
				path('public_chat/<room_id>/', PublicChatConsumer.as_asgi()),
			]
		)
	)
})