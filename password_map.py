class PasswordGroup(object):
	pass

class PasswordMap(object):
	"""Storage of groups of passwords in memory"""
	
	def __init__(self):
		self.groups = {}
	
	def addGroup(self, groupName):
		if groupName in self.groups:
			raise KeyError("Password group already exists")
		
		self.groups[groupName] = PasswordGroup()
