# Authors: Rodolfo Queiroz, Deangela Neves
# Nov 6, 2017
#
# This is the server side of the live chat application. 
# It contains:
#	All the recognized commands (requests) to be used such as 'sair', 'privado', 'nome' and so on. 
#	A main socket (socket_) to listen for connections .
# 	Two arrays: one to keep track of the connected users and the other for the private rooms.
# 

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
	# Socket for listening to connections (see __init__ method).
	socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	connected_users = [] # Connected users array.
	private_rooms = [] # Private Rooms array.

	# Initializer.
	def __init__(self):
		self.socket_.bind(('', 12345)) # Binds to localhost at port 12345.

	# Returns the string before parenthesis.
	# ex: get_request('nome(abc)') will return 'nome'.
	def get_request(self, request_str):
		return request_str[request_str.find(':') + 1 : request_str.find('(')]

	# Returns the string whithin the parenthesis.
	# ex: get_request('nome(abc)') will return 'abc'.
	def get_request_inner(self, request_str):
		return request_str[request_str.find('(') + 1 : request_str.find(')')]

	# Returns the first user which username in request_str matches a user in self.connected_users list.
	# ex: get_request_target('privado(joao)') will return the first (and only) user with username joao.
	def get_request_target(self, request_str):
		username = self.get_request_inner(request_str)
		return next((x for x in self.connected_users if x.username == username), None)

	# Returns a private room matching exactly the left_user (l_user), right_user (r_user) and agreed_on status
	# informed in the parameters, if any.
	def check_for_private_room(self, l_user, r_user, agreed_on): 
		return next((x for x in self.private_rooms if (x.left_user == l_user and x.right_user == r_user and x.agreed_on == agreed_on)), None)

	# Returns the first room in which the user is placed either as left_user or right_user, 
	# and both parties agreed, if any.
	def get_private_room(self, user):
		return next((x for x in self.private_rooms if (x.left_user == user or x.right_user == user and x.agreed_on == True)), None)		

	# Performs the procedure to properly disconnect a user.
	def user_disconnected(self, user):
		# If the user has requested for a private room and now wants to leave the server
		if user.room_identifier == "Pending":
			# Find the corresponding room by searching in self.private_rooms for one in which the user 
			# is placed as left_user and the right_user has not yet agreed, justifying the pending status
			# (See room_identifier in users.py for more understanding)
			p_room = next((x for x in self.private_rooms if (x.left_user == user and x.agreed_on == False)), None)
			if p_room: # If the room actually exists, remove it from the list
				self.private_rooms.remove(p_room)

		# Close the socket dedicated to this user and remove him/her from the connected_users list
		user.socket.close()
		self.connected_users.remove(user)

		# Now, send a message to the remaining users warning them about the one who just left
		user_left_str = "%s saiu..."%user.username
		print(user_left_str)

		for u in self.connected_users:
			u.send(user_left_str)

	# Sends a dictionary of users to the target in the specified format:
	# { 'ip:port': 'username', }
	# If send_to is None, the target will be the server itself, so it will just print the dictionary.
	# Otherwise, the target will be the user specified in the send_to parameter.
	def get_users_dict(self, send_to=None):
		user_list = json.dumps([{"%s:%s"%(u.ip, u.port): u.username} for u in self.connected_users])
		if send_to:
			data = bytes(json.dumps(user_list), 'utf-8')
			send_to.send(data)
		else:
			print(user_list)

	# Timeout response for a private room request
	def private_room_timed_out(self, p_room):
		# The right_user has not replied left_user's request for a private chat room so far (see private_room.py),
		# therefore the server is going to delete the object in order to save memory
		if p_room.agreed_on is False and p_room in self.private_rooms:
			# Display this information to the server
			print("Private Room requested by %s was not replied so it's being closed..."%p_room.left_user.username)
			# Send proper messages to both parties if they had not entered another private chat
			if p_room.left_user.room_identifier != "Private":
				p_room.left_user.send("------- Seu pedido ainda não foi respondido e por isso será excluido -------")
			if p_room.right_user.room_identifier == "Public":
				p_room.right_user.send("------- Você não respondeu o pedido de %s para sala privada e, por isso, o pedido será excluído -------"%p_room.left_user.username)
			# Fix the room_identifier for the left_user, which is staying at the public room
			p_room.left_user.room_identifier = "Public"
			# Remove the room from private_rooms list, zeroing the reference counter for p_room 
			# and, therefore, deleting the object
			self.private_rooms.remove(p_room)

	# This function is responsible for "staying" with a client and serve its needs by interpreting
	# the requests continuosly and sending back the appropriate response.
	def handler(self, client_socket, addr):
		# Create new user and append it to the list of connected users.
		current_user = User(addr[0], addr[1], client_socket)
		self.connected_users.append(current_user)

		while True:
			data = current_user.socket.recv(1024) # Receiving data from the current user.
			msg = str(data, 'utf-8') # Converting from data to string.
			request = self.get_request(msg) # Defining request prefix, which will define what to do next.
			print("%s: %s"%(current_user.username, msg)) # Printing 'user: request()' on the server prompt.

			if request == "nome": # If the user wants to set/change their name,
				# Get the content whithin the parenthesis to be the new username,
				new_username = self.get_request_inner(msg)
				# Check if the chosen username already exists,
				username_exists = next((x for x in self.connected_users if x.username == new_username), None) is not None
				# If it does, send a message back to the user so he/she may try again...
				if username_exists:
					existing_username_err = "Esse nickname ja existe"
					print(existing_username_err) # Also print this information on the server.
					current_user.send(existing_username_err)
				# If the chosen username does not exist, do the following:
				else:
					# If current_user was not assigned a username yet, it has just entered the chat
					# Otherwise, it has changed its username.
					# Therefore, let the other users know what is happening by creating a proper message
					# based on this checking.
					if current_user.username is None:
						message = "%s entrou..."%new_username
					else: 
						message = "%s agora é %s"%(current_user.username, new_username)
					
					# Transform the string into bytes, so it can further be sent to the users,
					data = bytes(message, 'utf-8')
					# Set the new username for the current user.
					current_user.username = new_username

			elif current_user.username == None: # If the user did not set his username yet,
				# Do not let him/her do anything else
				continue

			elif request == "lista": # If the user wants to see the list of connected users,
				# Send him/her the list by calling get_users_dict with the current_user as a parameter 
				# (see get_users_dict description).
				self.get_users_dict(current_user)
				continue

			elif request == "sair": # If the user wants to leave (the private room or the server),
				# Check where he/she is in right now: 
				# 	if they are in a private room, the request 'sair()' will lead them back to the public room;
				# 	if they are in the public room, the request 'sair()' will make them leave the server.

				# If the user is in a private room,
				if current_user.room_identifier == "Private":
					# Search for the room with the current user
					p_room = self.get_private_room(current_user)
					# If that room exists,
					if p_room: 
						# Create a message to inform both parties that the room is no longer available,
						back_to_public_str = "------- %s saiu do chat privado. Voltando para a sala publica -------"%current_user.username
						# Send them this message,
						p_room.send(back_to_public_str)
						# Set their room identifier back to Public (see users.py for more information on this)
						p_room.left_user.room_identifier = "Public"
						p_room.right_user.room_identifier = "Public"
						# Remove the room from the list
						self.private_rooms.remove(p_room)
					continue
				else:
					# Leave server
					self.user_disconnected(current_user)
					break

			elif request == "privado": # If the user wants to request a private chat with target,
				# If the user's room_identifier is not 'Public', either he has already made a request or 
				# he is already in a private room, so deny this request.
				if current_user.room_identifier != "Public":
					error_message = "Você já está em uma sala privada. Para participar de outra sala privada, primeiro você deve sair desta..."
					current_user.send(error_message)
				# Otherwise,
				else:
					# Get the user identified by the username within the parenthesis in the request,
					# called from now on by 'target'
					target = self.get_request_target(msg)
					# If the target exists,
					if target:
						# If the target is himself/herself,
						if target == current_user:
							# Don't waste your time
							current_user.send("~ Engraçadinh@... ~")
							continue
						# Check for the target's room_identifier.
						# The thinking here is similar to the one in line 183.
						elif target.room_identifier != "Public":
							error_message = "Private Room Requested: O usuário já se encontra ou aguarda por confirmação para entrar em uma sala privada, por favor tente mais tarde."
							current_user.send(error_message)
						# If the target is actually someone else available,
						else:
							# Print this information on the server,
							print("%s wants to start a private chat with %s\n"%(current_user.username, target.username))
							# Set the current user's room identifier to 'Pending'.
							# Here, the target's room identifier is not changed because, if so, he/she would not
							# be able to create requests for other users, being obligated to reply this...
							current_user.room_identifier = "Pending"
							# Create the private room requested for the current user 
							# Remember: the room has not being agreed on from both parties yet
							p_room = PrivateRoom(current_user, target)
							# Add the room to the private rooms list
							self.private_rooms.append(p_room)
							# Start a timer to remove this room from the list if the target does not reply
							# within 10 seconds.
							room_timer = Timer(10.0, self.private_room_timed_out, args=[p_room])
							room_timer.start()

							# Send proper messages to both parties
							confirmation_message = "-------\n%s deseja se conectar com você. \nPara aceitar, digite: aceito_privado(%s)\nPara recusar, digite: recuso_privado(%s)\n-------"%(current_user.username, current_user.username, current_user.username)
							waiting_message = "------- Aguardando por confirmação de %s para iniciar uma conversa privada... -------"%target.username
							target.send(confirmation_message)
							current_user.send(waiting_message)
					# If the target is actually another user,
					else:
						# Send error message back to the owner of the request
						current_user.send("Private Room Requested: Este usuário não está conectado.")
				continue
			
			elif request == "recuso_privado": # If the user denies a private chat request from target,
				target = self.get_request_target(msg) # Get target of the request
				# If the target exists,
				if target:
					# Find the room opened by the target and deleted it
					p_room = self.check_for_private_room(target, current_user, False)
					if p_room: # If the room actually exists,
						self.private_rooms.remove(p_room)
						# Set the target's room identifier back to 'Public' so he/she can
						# open new requests for private chats.
						target.room_identifier = "Public"

						# Print this information to the server
						print("%s denied to start a private chat with %s"%(current_user.username, target.username))
						
						# Create proper messages to both users
						target_message = "------- %s recusou seu pedido para iniciar uma conversa privada. -------"%current_user.username
						current_user_message = "------- Você recusou o pedido de %s para iniciar uma conversa privada. -------"%target.username
						# Send the messages
						target.send(target_message)
						current_user.send(current_user_message)
					# Otherwise, either it has already been closed or it was never created.
					else:
						current_user.send("Private Room Requested: Ou %s não requisitou uma sala privada com você ou a requisição foi invalidada por demora na resposta..."%target.username)
				 # If target does not exist, inform the user
				else:
					current_user.send("Private Room Requested: Este usuário não está conectado.")

				continue

			elif request == "aceito_privado": # If the user accepts to have a private chat with target,
				target = self.get_request_target(msg) # Get target of the request.
				# If the target exists,
				if target:
					# Find the room opened by the target.
					p_room = self.check_for_private_room(target, current_user, False)
					# If the room exists,
					if p_room:
						# Set its agreed on status to True as both parties agreed to have this private chat,
						p_room.agreed_on = True
						# Set the room identifer of both parties to 'Private', so their messages can be
						# identified as private (see user.py for more information),
						current_user.room_identifier = "Private"
						target.room_identifier = "Private"

						# Print this information to the server,
						print("%s accepted to start a private chat with %s"%(current_user.username, target.username))

						# Send a message to both parties informing them that they are now in a private chat.
						private_chat_started_str = "------- Chat Privado Entre %s e %s -------"%(current_user.username, target.username)
						target.send(private_chat_started_str)
						current_user.send(private_chat_started_str)
					# If the room does not exist, either it has already been closed or it was never created.
					else:
						current_user.send("Ou %s não requisitou uma sala privada com você ou a requisição foi invalidada por demora na resposta..."%target.username)	
				 # If target does not exist, inform the user
				else:
					current_user.send("Private Room Requested: Este usuário não está conectado.")
				continue


			else: # If the user sent an ordinary text,
				# Create the string to be shown, in the format: 'username escreveu: message'
				data = "%s escreveu: %s"%(current_user.username, str(data, 'utf-8'))

			# Print the string on the server
			print(data)

			# If the user is in a private room,
			if current_user.room_identifier == "Private":
				# Send the message to the private room only
				p_room = self.get_private_room(current_user)
				if p_room is not None:
					p_room.send(data)
			# Otherwise,
			else:
				# Send the message to everyone else who's in the public room
				for user in self.connected_users:
					if user.room_identifier != "Private":
						user.send(data)

			# Exception used to handle events related to a lost connection
			if not data or current_user.socket.fileno() == -1 or data == '':
				self.user_disconnected(current_user)
				break
	
	# Accepts client connections and creates an individual thread for each one that has been stablished
	def accept_connections(self):
		while True:
			client_socket,addr = self.socket_.accept()
			client_socket_thread = threading.Thread(target = self.handler, args = (client_socket, addr))
			client_socket_thread.daemon = True
			client_socket_thread.start()

	# Starts the server socket and the threads for each connected client 
	def run(self):
		self.socket_.listen(1) # Starts listening for connections

		# Creates a secondary thread to accept connections
		prompt_thread = threading.Thread(target = self.accept_connections)
		prompt_thread.daemon = True
		prompt_thread.start()

		# Print server status
		print("Servidor aceitando conexões...")

		while True:
			# Accepting for requests within the server
			command = input()

			if command[: command.find('(')] == "lista":
				self.get_users_dict()

			elif command[: command.find('(')] == "sair":
				break

			else:
				print("Erro: esse comando nao é reconhecido pelo sistema")


if __name__ == "__main__":
	server = ChatServer()
	server.run()