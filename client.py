import socket
import threading 
import sys

class ChatClient:

	socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def send_message(self):

		while True:
			self.socket_.send(bytes('escreveu:' + input(""), 'utf-8'))

	def __init__(self, address):

		username = input("Entre com um nickname:\n")

		if username:
			self.socket_.connect((address, 12345))
			self.socket_.send(bytes(username, 'utf-8'))

			user_thread = threading.Thread(target = self.send_message)
			user_thread.daemon = True
			user_thread.start()

			while True:

				data = self.socket_.recv(1024)

				if not data:
					break
				print(str(data, 'utf-8'))

client = ChatClient(sys.argv[1])