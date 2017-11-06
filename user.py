class User(object):
	ip = None
	port = None
	socket = None
	username = None
	room_identifier = "Public" # Public / Pending / Private

	def __init__(self, ip, port, socket):
		super(User, self).__init__()
		self.ip = ip
		self.port = port
		self.socket = socket

	def __str__(self):
		return "Address: %s:%s | Username: %s"%(self.ip, self.port, self.username)	

	def __dict__(self):
		return {self.socket.getsockname(): self.username}

	def send(self, message):
		if self.socket.fileno() != -1: # fileno() returns -1 for dead sockets
			canonical_type = type(message)
			if canonical_type is str:
				self.socket.send(bytes(message, 'utf-8'))
			elif canonical_type is bytes:
				self.socket.send(message)
		else:
			print("%s's socket is dead..."%self.username)