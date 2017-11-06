from user import *

class PrivateRoom(object):
	left_user = None
	right_user = None
	agreed_on = False

	def __init__(self, l_user, r_user):
		super(PrivateRoom, self).__init__()
		self.left_user = l_user
		self.right_user = r_user

	def send(self, message):
		if self.agreed_on is True:
			self.left_user.send(message)
			self.right_user.send(message)
		else:
			print("This room is not ready (requested by: %s)!"%self.left_user.username)