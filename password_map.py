import struct

## On-disk format
#
# 32 bytes	AES-CBC-encrypted wrappedOuterKey
# 32 bytes	IV
#  4 bytes	size of data following (N)
#  N bytes	AES-GCM encrypted blob containing pickled structure for password map

class Magic(object):
	"""
	Few magic constant definitions so that we know which nodes to search
	for keys.
	"""
	u = lambda fmt, s: struct.unpack(fmt, s)[0]
	hdr = u("!I", "TZPW")
	
	unlockNode = [hdr, u("!I", "ULCK")] # for unlocking wrapped AES-GCM key
	groupNode  = [hdr, u("!I", "GRUP")] # for generating keys for individual password groups
	unlockKey = "TrezorPassMasterKey" # string to derive wrapping key from
	
class PasswordGroup(object):
	pass

class PasswordMap(object):
	"""Storage of groups of passwords in memory"""
	
	def __init__(self, trezor):
		assert trezor is not None
		self.groups = {}
		self.trezor = trezor
		self.outerKey = None # outer AES-GCM key
	
	def addGroup(self, groupName):
		if groupName in self.groups:
			raise KeyError("Password group already exists")
		
		self.groups[groupName] = PasswordGroup()

	def fromDisk(self, fname):
		"""
		Load encrypted passwords from disk file, decrypt outer
		layer containing key names. Requires Trezor connected.
		"""
		pass
	
	def toDisk(self, fname):
		"""
		Write password database to disk, encrypt it. Requires Trezor
		connected.
		"""
		pass
	
	def unwrapKey(self, wrappedOuterKey):
		"""
		Decrypt wrapped AES-GCM key using Trezor.
		"""
		ret = self.trezor.decrypt_keyvalue(Magic.unlockNode, Magic.unlockKey, wrappedOuterKey, ask_on_encrypt=False, ask_on_decrypt=True)
		return ret
		
	def wrapKey(self, keyToWrap):
		"""
		Encrypt/wrap a key. Its size must be multiple of 16.
		"""
		ret = self.trezor.encrypt_keyvalue(Magic.unlockNode, Magic.unlockKey, keyToWrap, ask_on_encrypt=False, ask_on_decrypt=True)
		return ret
		
		