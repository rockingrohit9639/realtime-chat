from django.core.serializers.python import Serializer
from django.core.paginator import Paginator
from django.core.serializers import serialize
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.utils import timezone
from django.contrib.auth import get_user_model
from private_chat.exceptions import ClientError
from public_chat.models import PublicChatRoom, PublicChatMessage
from private_chat.utils import calculate_timestamp

User = get_user_model()

MSG_TYPE_MESSAGE = 0
DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE = 10


class PublicChatConsumer(AsyncJsonWebsocketConsumer):

	async def connect(self):
		print("PublicChatConsumer: connect: " + str(self.scope["user"]))
		await self.accept()
		self.room_id = None

	async def disconnect(self, code):
		try:
			if self.room_id != None:
				await self.leave_room(self.room_id)
		except Exception:
			pass

	async def receive_json(self, content):
		command = content.get("command", None)
		try:
			if command == "send":
				if len(content["message"].lstrip()) != 0:
					await self.send_room(content["room_id"], content["message"])
			elif command == "join":
				# Make them join the room
				await self.join_room(content["room"])
			elif command == "leave":
				# Leave the room
				await self.leave_room(content["room"])
			elif command == "get_room_chat_messages":
				await self.display_progress_bar(True, content["room_id"])
				room = await get_room_or_error(content['room_id'])
				payload = await get_room_chat_messages(room, content['page_number'])
				if payload is not None:
					payload = json.loads(payload)
					await self.send_messages_payload(payload['messages'], payload['new_page_number'], content["room_id"])
				else:
					raise ClientError("FETCH_MSG_ERROR", "Something went wrong retrieving the chatroom messages.")
				await self.display_progress_bar(False, content["room_id"])
		except ClientError as e:
			await self.display_progress_bar(False, content["room_id"])
			await self.handle_client_error(e)

	async def send_room(self, room_id, message):
		if self.room_id is not None:
			if str(room_id) != str(self.room_id):
				raise ClientError("ROOM_ACCESS_DENIED", "Room access denied")
			if not is_authenticated(self.scope["user"]):
				raise ClientError("AUTH_ERROR", "You must be authenticated to chat.")
		else:
			raise ClientError("ROOM_ACCESS_DENIED", "Room access denied")

		# Get the room and send to the group about it
		room = await get_room_or_error(room_id)
		await create_public_room_chat_message(room, self.scope["user"], message)

		await self.channel_layer.group_send(
			room.group_name,
			{
				"type": "chat.message",
				"profile_image": self.scope["user"].profile_image.url,
				"username": self.scope["user"].username,
				"user_id": self.scope["user"].id,
				"message": message,
			}
		)

	async def chat_message(self, event):
		timestamp = calculate_timestamp(timezone.now())
		await self.send_json(
			{
				"msg_type": MSG_TYPE_MESSAGE,
				"profile_image": event["profile_image"],
				"username": event["username"],
				"user_id": event["user_id"],
				"message": event["message"],
				"natural_timestamp": timestamp,
			},
		)

	async def join_room(self, room_id):
		is_auth = is_authenticated(self.scope["user"])
		try:
			room = await get_room_or_error(room_id)
		except ClientError as e:
			await self.handle_client_error(e)

		# Add user to "users" list for room
		if is_auth:
			await connect_user(room, self.scope["user"])

		# Store that we're in the room
		self.room_id = room.id

		# Add them to the group so they get room messages
		await self.channel_layer.group_add(
			room.group_name,
			self.channel_name,
		)

		# Instruct their client to finish opening the room
		await self.send_json({
			"join": str(room.id)
		})

	async def leave_room(self, room_id):
		is_auth = is_authenticated(self.scope["user"])
		room = await get_room_or_error(room_id)

		# Remove user from "users" list
		if is_auth:
			await disconnect_user(room, self.scope["user"])

		# Remove that we're in the room
		self.room_id = None
		# Remove them from the group so they no longer get room messages
		await self.channel_layer.group_discard(
			room.group_name,
			self.channel_name,
		)

	async def handle_client_error(self, e):
		errorData = {}
		errorData['error'] = e.code
		if e.message:
			errorData['message'] = e.message
			await self.send_json(errorData)
		return

	async def send_messages_payload(self, messages, new_page_number, room_id):
		room = await get_room_or_error(room_id)
		total_users = await get_num_connected_users(room)
		await self.send_json(
			{
				"messages_payload": "messages_payload",
				"messages": messages,
				"new_page_number": new_page_number,
				"total_users": total_users
			},
		)

	async def display_progress_bar(self, is_displayed, room_id):
		room = await get_room_or_error(room_id)
		total_users = await get_num_connected_users(room)
		await self.send_json(
			{
				"display_progress_bar": is_displayed,
				"total_users": total_users,
			}
		)


def is_authenticated(user):
	if user.is_authenticated:
		return True
	return False


@database_sync_to_async
def create_public_room_chat_message(room, user, message):
	return PublicChatMessage.objects.create(user=user, room=room, content=message)


@database_sync_to_async
def connect_user(room, user):
	return room.connect_user(user)


@database_sync_to_async
def disconnect_user(room, user):
	return room.disconnect_user(user)


@database_sync_to_async
def get_room_or_error(room_id):
	try:
		room = PublicChatRoom.objects.get(pk=room_id)
	except PublicChatRoom.DoesNotExist:
		raise ClientError("ROOM_INVALID", "Invalid room.")
	return room


@database_sync_to_async
def get_num_connected_users(room):
	if room.users:
		return len(room.users.all())
	return 0


@database_sync_to_async
def get_room_chat_messages(room, page_number):
	try:
		qs = PublicChatMessage.objects.by_room(room)
		p = Paginator(qs, DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE)

		payload = {}
		messages_data = None
		new_page_number = int(page_number)
		if new_page_number <= p.num_pages:
			new_page_number = new_page_number + 1
			s = LazyRoomChatMessageEncoder()
			payload['messages'] = s.serialize(p.page(page_number).object_list)
		else:
			payload['messages'] = "None"
		payload['new_page_number'] = new_page_number
		return json.dumps(payload)
	except Exception as e:
		print("EXCEPTION: " + str(e))
		return None


class LazyRoomChatMessageEncoder(Serializer):
	def get_dump_object(self, obj):
		dump_object = {}
		dump_object.update({'msg_type': MSG_TYPE_MESSAGE})
		dump_object.update({'msg_id': str(obj.id)})
		dump_object.update({'user_id': str(obj.user.id)})
		dump_object.update({'username': str(obj.user.username)})
		dump_object.update({'message': str(obj.content)})
		dump_object.update({'profile_image': str(obj.user.profile_image.url)})
		dump_object.update({'natural_timestamp': calculate_timestamp(obj.timestamp)})
		return dump_object















