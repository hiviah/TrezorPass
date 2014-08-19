import struct
import cPickle

from Crypto.Cipher import AES

## On-disk format
#
# 32 bytes	AES-CBC-encrypted wrappedOuterKey
# 16 bytes	IV
#  4 bytes	size of data following (N)
#  N bytes	AES-GCM encrypted blob containing pickled structure for password map
# 16 bytes	GMAC

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
	
class Padding(object):
	"""
	PKCS#5 Padding for block cipher having 16-byte blocks
	"""
	BS = 16 #blocksize
	pad = lambda s: s + (Padding.BS - len(s) % Padding.BS) * chr(Padding.BS - len(s) % Padding.BS)
	unpad = lambda s : s[0:-ord(s[-1])]
	
class PasswordGroup(object):
	pass

class PasswordMap(object):
	"""Storage of groups of passwords in memory"""
	
	def __init__(self, trezor):
		assert trezor is not None
		self.groups = {}
		self.trezor = trezor
		self.outerKey = None # outer AES-GCM key
		self.outerIv = None  # IV for data blob encrypted with outerKey
	
	def addGroup(self, groupName):
		groupName = str(groupName)
		if groupName in self.groups:
			raise KeyError("Password group already exists")
		
		self.groups[groupName] = PasswordGroup()

	def load(self, fname):
		"""
		Load encrypted passwords from disk file, decrypt outer
		layer containing key names. Requires Trezor connected.
		
		@throws IOError: if reading file failed
		"""
		with file(fname) as f:
			wrappedKey = f.read(32)
			if len(wrappedKey) != 32:
				raise IOError("Corrupted disk format - bad wrapped key length")
			
			self.outerKey = self.unwrapKey(wrappedKey)
			
			self.outerIv = f.read(16)
			if len(self.outerIv) != 16:
				raise IOError("Corrupted disk format - bad IV length")
			
			ls = f.read(4)
			if len(ls) != 4:
				raise IOError("Corrupted disk format - bad data length")
			l = struct.unpack("!I", ls)[0]
			
			encrypted = f.read(l)
			if len(encrypted) != l:
				raise IOError("Corrupted disk format - not enough data bytes")
			
			serialized = encrypted #TODO: AES-GCM
			self.groups = cPickle.loads(serialized)
	
	def save(self, fname):
		"""
		Write password database to disk, encrypt it. Requires Trezor
		connected.
		
		@throws IOError: if writing file failed
		"""
		assert len(self.outerKey) == 32
		assert len(self.outerIv) == 16
		wrappedKey = self.wrapKey(self.outerKey)
		
		with file(fname, "wb") as f:
			f.write(wrappedKey)
			f.write(self.outerIv)
			serialized = cPickle.dumps(self.groups)
			encrypted = serialized #todo AES-GCM
			l = struct.pack("!I", len(encrypted))
			f.write(l)
			f.write(encrypted)
			f.flush()
			f.close()
	
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
		
		