# Authors: Rodolfo Queiroz, Deangela Neves
# Nov 6, 2017
# 
# The ChatClient class represents the client side of a TCP conection in a live chat based application
# It contains a main thread responsible for receiving the data from the server while writing data to 
# that same server using a second thread, here called 'user_thread'.
#



import socket
import threading 
import sys

class ChatClient:
	# Initializing client socket
	socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	# This function will be used in a secondary thread in order 
	# to always be able to write requests to the server
	def send_message(self):
		while True:
			self.socket_.send(bytes(input(""), 'utf-8'))

	def __init__(self, address):
		# Asks the user for a username before connecting to the server
		username = input("Entre com um nickname: ")

		# Uses the input to write the request nome(username) and send it to the server
		if username:
			message = "nome(%s)"%username
			self.socket_.connect((address, 12345))
			self.socket_.send(bytes(message, 'utf-8'))

			# Once the connection is stabilished and the first data sent,
			# the thread bellow is created for writing to the server at the
			# same time that data is received
			user_thread = threading.Thread(target = self.send_message)
			user_thread.daemon = True
			user_thread.start()

			while True:
				# receiving data
				data = self.socket_.recv(1024)

				if not data:
					break

				# printing data to the user
				print(str(data, 'utf-8'))

client = ChatClient(sys.argv[1])