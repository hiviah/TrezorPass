import struct
import cPickle
import hmac
import hashlib
import os

from Crypto.Cipher import AES

## On-disk format
#
# 32 bytes	AES-CBC-encrypted wrappedOuterKey
# 16 bytes	IV
#  2 bytes	backup private key size (B)
#  B bytes	encrypted backup key
#  4 bytes	size of data following (N)
#  N bytes	AES-CBC encrypted blob containing pickled structure for password map
# 32 bytes	HMAC-SHA256 over data with same key as AES-CBC data struct above

BLOCKSIZE = 16
MACSIZE = 32
KEYSIZE = 32

class Magic(object):
	"""
	Few magic constant definitions so that we know which nodes to search
	for keys.
	"""
	u = lambda fmt, s: struct.unpack(fmt, s)[0]
	hdr = u("!I", "TZPW")
	
	unlockNode = [hdr, u("!I", "ULCK")] # for unlocking wrapped AES-CBC key
	groupNode  = [hdr, u("!I", "GRUP")] # for generating keys for individual password groups
	unlockKey = "TrezorPassMasterKey" # string to derive wrapping key from
	
class Padding(object):
	"""
	PKCS#5 Padding for block cipher having 16-byte blocks
	"""
	BS = BLOCKSIZE
	
	@staticmethod
	def pad(s):
		return s + (Padding.BS - len(s) % Padding.BS) * chr(Padding.BS - len(s) % Padding.BS)
	
	@staticmethod
	def unpad(s):
		return s[0:-ord(s[-1])]
	
class PasswordGroup(object):
	pass

class PasswordMap(object):
	"""Storage of groups of passwords in memory"""
	
	def __init__(self, trezor):
		assert trezor is not None
		self.groups = {}
		self.trezor = trezor
		self.outerKey = None # outer AES-CBC key
		self.outerIv = None  # IV for data blob encrypted with outerKey
		self.encryptedBackupKey = None
	
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
			wrappedKey = f.read(KEYSIZE)
			if len(wrappedKey) != KEYSIZE:
				raise IOError("Corrupted disk format - bad wrapped key length")
			
			self.outerKey = self.unwrapKey(wrappedKey)
			
			self.outerIv = f.read(BLOCKSIZE)
			if len(self.outerIv) != BLOCKSIZE:
				raise IOError("Corrupted disk format - bad IV length")
			
			lb = f.read(2)
			if len(lb) != 2:
				raise IOError("Corrupted disk format - bad backup key length")
			lb = struct.unpack("!H", lb)[0]
			
			self.encryptedBackupKey = f.read(lb)
			if len(self.encryptedBackupKey) != lb:
				raise IOError("Corrupted disk format - not enough encrypted backup key bytes")
			
			ls = f.read(4)
			if len(ls) != 4:
				raise IOError("Corrupted disk format - bad data length")
			l = struct.unpack("!I", ls)[0]
			
			encrypted = f.read(l)
			if len(encrypted) != l:
				raise IOError("Corrupted disk format - not enough data bytes")
			
			hmacDigest = f.read(MACSIZE)
			if len(hmacDigest) != MACSIZE:
				raise IOError("Corrupted disk format - HMAC not complete")
			
			#time-invariant HMAC comparison that also works with python 2.6
			newHmacDigest = hmac.new(self.outerKey, encrypted, hashlib.sha256).digest()
			hmacCompare = 0
			for (ch1, ch2) in zip(hmacDigest, newHmacDigest):
				hmacCompare |= int(ch1 != ch2)
			if hmacCompare != 0:
				raise IOError("Corrupted disk format - HMAC does not match")
				
			serialized = self.decryptOuter(encrypted, self.outerIv)
			self.groups = cPickle.loads(serialized)
	
	def save(self, fname):
		"""
		Write password database to disk, encrypt it. Requires Trezor
		connected.
		
		@throws IOError: if writing file failed
		"""
		assert len(self.outerKey) == KEYSIZE
		self.outerIv = os.urandom(BLOCKSIZE)
		wrappedKey = self.wrapKey(self.outerKey)
		
		with file(fname, "wb") as f:
			f.write(wrappedKey)
			f.write(self.outerIv)
			serialized = cPickle.dumps(self.groups)
			encrypted = self.encryptOuter(serialized, self.outerIv)
			
			hmacDigest = hmac.new(self.outerKey, encrypted, hashlib.sha256).digest()
			lb = struct.pack("!H", len(self.encryptedBackupKey))
			f.write(lb)
			f.write(self.encryptedBackupKey)
			l = struct.pack("!I", len(encrypted))
			f.write(l)
			f.write(encrypted)
			f.write(hmacDigest)
			
			f.flush()
			f.close()
			
	def encryptOuter(self, plaintext, iv):
		"""
		Pad and encrypt with self.outerKey
		"""
		return self.encrypt(plaintext, iv, self.outerKey)
	
	def encrypt(self, plaintext, iv, key):
		"""
		Pad plaintext with PKCS#5 and encrypt it.
		"""
		cipher = AES.new(key, AES.MODE_CBC, iv)
		padded = Padding.pad(plaintext)
		return cipher.encrypt(padded)
	
	def decryptOuter(self, ciphertext, iv):
		"""
		Decrypt with self.outerKey and unpad
		"""
		return self.decrypt(ciphertext, iv, self.outerKey)
		
	def decrypt(self, ciphertext, iv, key):
		"""
		Decrypt ciphertext, unpad it and return
		"""
		cipher = AES.new(key, AES.MODE_CBC, iv)
		plaintext = cipher.decrypt(ciphertext)
		unpadded = Padding.unpad(plaintext)
		return unpadded
	
	def unwrapKey(self, wrappedOuterKey):
		"""
		Decrypt wrapped outer key using Trezor.
		"""
		ret = self.trezor.decrypt_keyvalue(Magic.unlockNode, Magic.unlockKey, wrappedOuterKey, ask_on_encrypt=False, ask_on_decrypt=True)
		return ret
		
	def wrapKey(self, keyToWrap):
		"""
		Encrypt/wrap a key. Its size must be multiple of 16.
		"""
		ret = self.trezor.encrypt_keyvalue(Magic.unlockNode, Magic.unlockKey, keyToWrap, ask_on_encrypt=False, ask_on_decrypt=True)
		return ret
		
		