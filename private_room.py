# Authors: Rodolfo Queiroz, Deangela Neves
# Nov 6, 2017
#
# PrivateRoom represents a private room in this live chat application.
#

from user import *

class PrivateRoom(object):
	# The user who requested the private room
	left_user = None
	# The user who accepted the request
	right_user = None
	# Whether or not right_user has accepted the request
	agreed_on = False

	# Initializer
	def __init__(self, l_user, r_user):
		super(PrivateRoom, self).__init__()
		self.left_user = l_user
		self.right_user = r_user

	# Send messages to both parties using the send method defined in User class
	def send(self, message):
		if self.agreed_on is True:
			self.left_user.send(message)
			self.right_user.send(message)
		else:
			print("This room is not ready (requested by: %s)!"%self.left_user.username)