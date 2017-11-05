import socket
import threading 
import sys
import time
from itertools import chain
import json

class ChatServer:

	socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	connections = []

	users = {}

	map_user_connection = {}

	def __init__(self):

		self.socket_.bind(('0.0.0.0', 12345))

		self.socket_.listen(1)

	def handler(self, client_socket, addr):
		while True:

			data = client_socket.recv(1024)

			msg = str(data, 'utf-8')

			if msg[msg.find(':') + 1 : msg.find('(')] == "nome":
				nickname = msg[msg.find('(') + 1 : msg.find(')')]

				if nickname in self.users.values():
					print("esse nickname ja existe")
				else:
					if (addr[0], addr[1]) in self.users.keys():
						data = bytes(self.users[(addr[0], addr[1])] + " agora é " + nickname, 'utf-8')
					else:
						data = bytes(nickname + " entrou...", 'utf-8')
					self.users[(addr[0], addr[1])] = nickname
					self.map_user_connection[nickname] = client_socket
				

			elif msg[msg.find(':') + 1 : msg.find('(')] == "lista":

				k = list(self.users.keys())
				v = list(self.users.values())

				user_list = list(zip(v, k))

				data = json.dumps(user_list)
				client_socket.send(bytes(data, 'utf-8'))
				continue

			elif msg[msg.find(':') + 1 : msg.find('(')] == "sair":

				username = self.users[(addr[0], addr[1])]
				print(username + " saiu!")

				for connection in self.connections:
					connection.send(bytes(username + " saiu!", 'utf-8'))

				self.users.pop((addr[0], addr[1]), None)
				self.connections.remove(client_socket)

				client_socket.close()
				break

			elif msg[msg.find(':') + 1 : msg.find('(')] == "privado":
				pass
				"""
				nickname = msg[msg.find('(') + 1 : msg.find(')')]
				invitation = self.users[(addr[0], addr[1])] + " deseja se conectar com você. Você aceita a conexão?(s ou n)"

				destination = self.map_user_connection[nickname]
				destination.send(bytes(invitation, 'utf-8'))
				"""

			else:
				msg = self.users[(addr[0], addr[1])] + ' '+ str(data, 'utf-8')
				data = bytes(msg, 'utf-8')


		
			for connection in self.connections:
				connection.send(data)
			print(str(data, 'utf-8'))

			if not data:

				username = self.users[(addr[0], addr[1])]
				print(username + " saiu!")

				for connection in self.connections:
					connection.send(bytes(username + " saiu!", 'utf-8'))

				self.users.pop((addr[0], addr[1]), None)
				self.connections.remove(client_socket)

				client_socket.close()
				break
			
	def run(self):

		prompt_thread = threading.Thread(target = self.accept_connections)
		prompt_thread.daemon = True
		prompt_thread.start()

		while True:
			command = input()

			if command[: command.find('(')] == "lista":

				k = list(self.users.keys())
				v = list(self.users.values())

				user_list = list(zip(v, k))

				print(user_list)

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

			self.connections.append(client_socket)


server = ChatServer()
server.run()