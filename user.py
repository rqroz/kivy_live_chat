# Authors: Rodolfo Queiroz, Deangela Neves
# Nov 6, 2017
#
# The User class represents the user in this live chat application 
# and its attributes/methods are very straightforward.
#

class User(object):
	ip = None # Holds the ip from the connection
	port = None # Holds the port used in the connection
	socket = None # Holds the socket being used to maintain communication between the client/server sides
	username = None # Holds the username to be displayed
	# The room_identifier attribute bellow may contain 3 values: Public / Pending / Private
	# These values are strings and they define the status of the user related to which room he's currently in. 
	# 'Public' means the general (or public) room
	# 'Private' means that this user is currently in a private room with someone else 
	# 'Pending' means that this user has opened a request for a private room but had not yet been replied
	room_identifier = "Public"

	# Initializer
	def __init__(self, ip, port, socket):
		super(User, self).__init__()
		self.ip = ip
		self.port = port
		self.socket = socket

	# String method
	def __str__(self):
		return "Address: %s:%s | Username: %s"%(self.ip, self.port, self.username)	

	# This method sends a message to the current user using its socket
	def send(self, message):		
		# Check wheter 'message' is a string or data type
		canonical_type = type(message)
		# and place the proper content in 'data' according to the previous check
		data = bytes(message, 'utf-8') if canonical_type is str else message

		try:
			self.socket.send(data)
		except Exception as err:
			# This exception will occur if the socket has suddenly closed
			# Broken Pipe / SIGPIPE are known errors when the user cancels the connection with ctrl + c
			print("Error while sending data to %s: %s"%(self.username, err))
			self.socket.close()