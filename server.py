import socket
import threading 
import sys
import time
import json

from threading import Timer
from itertools import chain

from user import *
from private_room import *

class ChatServer:

	socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	connected_users = []
	private_rooms = []

	def __init__(self):

		self.socket_.bind(('0.0.0.0', 12345))

		self.socket_.listen(1)

	def get_request(self, request_str):
		return request_str[request_str.find(':') + 1 : request_str.find('(')]

	def get_request_inner(self, request_str):
		return request_str[request_str.find('(') + 1 : request_str.find(')')]

	def get_request_target(self, request_str):
		username = self.get_request_inner(request_str)
		return next((x for x in self.connected_users if x.username == username), None)

	def check_for_private_room(self, l_user, r_user, agreed_on): # Returns the first room with the passed agreed_on status and with the left user and right user specified
		return next((x for x in self.private_rooms if (x.left_user == l_user and x.right_user == r_user and x.agreed_on == agreed_on)), None)

	def get_private_room(self, user): # Returns the first room in which the user is placed either as left_user or right_user and both parties agreed 
		return next((x for x in self.private_rooms if (x.left_user == user or x.right_user == user and x.agreed_on == True)), None)		

	def user_disconnected(self, user):
		if user.room_identifier == "Pending":
			p_room = next((x for x in self.private_rooms if (x.left_user == user and x.agreed_on == False)), None)
			if p_room:
				self.private_rooms.remove(p_room)

		user.socket.close()
		self.connected_users.remove(user)

		user_left_str = "%s saiu..."%user.username
		print(user_left_str)

		for u in self.connected_users:
			u.send(user_left_str)

	def get_users_list(self, send_to=None):
		user_list = json.dumps([{"%s:%s"%(u.ip, u.port): u.username} for u in self.connected_users])
		if send_to:
			data = bytes(json.dumps(user_list), 'utf-8')
			send_to.send(data)
		else:
			print(user_list)

	def private_room_timed_out(self, p_room):
		# right_user has not replied left_user's request for a private chat room so far,
		# therefore the server is going to delete the object ('the request/room') in order to save memory
		if p_room.agreed_on is False and p_room in self.private_rooms:
			print("Private Room requested by %s was not replied so it's being closed..."%p_room.left_user.username)
			p_room.left_user.send("------- Seu pedido ainda não foi respondido e por isso será excluido -------")
			p_room.right_user.send("------- Você não respondeu o pedido de %s para sala privada e, por isso, o pedido será excluído -------"%p_room.left_user.username)
			p_room.left_user.room_identifier = "Public"
			self.private_rooms.remove(p_room)

	def handler(self, client_socket, addr):
		# Create new user and append it to the list of connected users
		current_user = User(addr[0], addr[1], client_socket)
		self.connected_users.append(current_user)


		while True:
			data = current_user.socket.recv(1024)

			msg = str(data, 'utf-8')
			request = self.get_request(msg)
			print("%s: %s"%(current_user.username, msg))

			if request == "nome":
				new_username = self.get_request_inner(msg)
				username_exists = next((x for x in self.connected_users if x.username == new_username), None) is not None
				if username_exists:
					existing_username_err = "Esse nickname ja existe"
					print(existing_username_err)
					current_user.send(existing_username_err)
				else:
					# if current_user was not assigned a username yet, it has just entered the chat
					if current_user.username is None:
						message = "%s entrou..."%new_username
					# otherwise it has changed its username
					else: 
						message = "%s agora é %s"%(current_user.username, new_username)
					
					data = bytes(message, 'utf-8')
					
					current_user.username = new_username

			elif request == "lista":
				self.get_users_list(current_user)
				continue

			elif request == "sair":
				if current_user.room_identifier == "Private":
					# Leave private room
					back_to_public_str = "------- %s saiu do chat privado. Voltando para a sala publica -------"%current_user.username
					p_room = self.get_private_room(current_user)
					if p_room:
						p_room.send(back_to_public_str)
						p_room.left_user.room_identifier = "Public"
						p_room.right_user.room_identifier = "Public"
						self.private_rooms.remove(p_room)
					continue
				else:
					# Leave server
					self.user_disconnected(current_user)
					break

			elif request == "privado":
				if current_user.room_identifier != "Public":
					error_message = "Você já está em uma sala privada. Para participar de outra sala privada, primeiro você deve sair desta..."
					current_user.send(error_message)
				else:
					print(self.connected_users)
					target = self.get_request_target(msg)
					print(self.connected_users)
					if target == current_user:
						current_user.send("Engraçadinh@...")
						continue
					if target:
						if target.room_identifier != "Public":
							error_message = "O usuário já se encontra ou aguarda por confirmação para entrar em uma sala privada, por favor tente mais tarde."
							current_user.send(error_message)
						else:
							print("%s wants to start a private chat with %s\n"%(current_user.username, target.username))
							# Creating the private room requested for the current user 
							current_user.room_identifier = "Pending"
							p_room = PrivateRoom(current_user, target)
							self.private_rooms.append(p_room)
							room_timer = Timer(10.0, self.private_room_timed_out, args=[p_room])
							room_timer.start()

							confirmation_message = "%s deseja se conectar com você. \nPara aceitar, digite: aceito_privado(%s)\nPara recusar, digite: recuso_privado(%s)"%(current_user.username, current_user.username, current_user.username)
							waiting_message = "Aguardando por confirmação de %s para iniciar uma conversa privada..."%target.username
							target.send(confirmation_message)
							current_user.send(waiting_message)

					else:
						# Send error message back to the owner of the request
						current_user.send("Este usuário não está conectado.")
				continue
			elif current_user.username == None:
				continue
			elif request == "recuso_privado":
				target = self.get_request_target(msg) # Get target of the request
				if target:
					# Find the room opened by the target and deleted it
					p_room = self.check_for_private_room(target, current_user, False)
					if p_room:
						self.private_rooms.remove(p_room)
						target.room_identifier = "Public"

						# send messages to both users
						print("%s denied to start a private chat with %s"%(current_user.username, target.username))
						target_message = "%s recusou seu pedido para iniciar uma conversa privada."%current_user.username
						current_user_message = "Você recusou o pedido de %s para iniciar uma conversa privada."%target.username
						
						target.send(target_message)
						current_user.send(current_user_message)
					else:
						current_user.send("Ou %s não requisitou uma sala privada com você ou a requisição foi invalidada por demora na resposta..."%target.username)
				else:
					current_user.send("Este usuário não está conectado.")

				continue

			elif request == "aceito_privado":
				target = self.get_request_target(msg) # Get target of the request
				if target:
					# Find the room opened by the target and deleted it
					p_room = self.check_for_private_room(target, current_user, False)
					if p_room:
						p_room.agreed_on = True
						current_user.room_identifier = "Private"
						target.room_identifier = "Private"

						print("%s accepted to start a private chat with %s"%(current_user.username, target.username))
						private_chat_started_str = "------- Chat Privado Entre %s e %s -------"%(current_user.username, target.username)
						target.send(private_chat_started_str)
						current_user.send(private_chat_started_str)
					else:
						current_user.send("Ou %s não requisitou uma sala privada com você ou a requisição foi invalidada por demora na resposta..."%target.username)	
				else:
					current_user.send("Este usuário não está conectado.")
				continue
			else:
				data = "%s escreveu: %s"%(current_user.username, str(data, 'utf-8'))


			print(data)
			if current_user.room_identifier == "Private":
				# Send message to private room
				p_room = self.get_private_room(current_user)
				if p_room is not None:
					p_room.send(data)
			else:
				# Send message to everyone
				for user in self.connected_users:
					if user.room_identifier == "Public":
						user.send(data)

			if not data or current_user.socket.fileno() == -1:
				self.user_disconnected(current_user)
				break
			
	def run(self):

		prompt_thread = threading.Thread(target = self.accept_connections)
		prompt_thread.daemon = True
		prompt_thread.start()
		print("Servidor aceitando conexões...")

		while True:
			command = input()

			if command[: command.find('(')] == "lista":
				self.get_users_list()

			elif command[: command.find('(')] == "sair":
				break

			else:
				print("Erro: esse comando nao é reconhecido pelo sistema")

	def accept_connections(self):
		while True:

			client_socket,addr = self.socket_.accept()

			client_socket_thread = threading.Thread(target = self.handler, args = (client_socket, addr))
			client_socket_thread.daemon = True
			client_socket_thread.start()


server = ChatServer()
server.run()