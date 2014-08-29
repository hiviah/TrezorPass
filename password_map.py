import struct
import cPickle
import hmac
import hashlib

from Crypto.Cipher import AES
from Crypto import Random

## On-disk format
#  4 bytes	header "TZPW"
#  4 bytes	data storage version, network order uint32_t
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
	headerStr = "TZPW"
	hdr = u("!I", headerStr)
	
	unlockNode = [hdr, u("!I", "ULCK")] # for unlocking wrapped AES-CBC key
	groupNode  = [hdr, u("!I", "GRUP")] # for generating keys for individual password groups
	#the unlock and backup key is written in this weird way to fit display nicely
	unlockKey = "Decrypt master  key?" # string to derive wrapping key from
	
	backupNode = [hdr, u("!I", "BKUP")] # for unlocking wrapped backup private RSA key
	backupKey = "Decrypt backup  key?" # string to derive backup wrapping key from
	
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
	
	def __init__(self):
		self.pairs = []
	
	def addPair(self, key, encryptedValue):
		"""Add key-value pair"""
		self.pairs.append((key, encryptedValue))
	
	def removePair(self, idx):
		"""Remove pair at given index"""
		self.pairs.pop(idx)
	
	def updatePair(self, idx, key, encryptedValue):
		"""Update pair at index idx with given key and value"""
		self.pairs[idx] = (key, encryptedValue)
		
	def pair(self, idx):
		"""Return pair with given index"""
		return self.pairs[idx]

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
		"""
		Add group by name as utf-8 encoded string
		"""
		groupName = groupName
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
			header = f.read(len(Magic.headerStr))
			if header != Magic.headerStr:
				raise IOError("Bad header in storage file")
			version = f.read(4)
			if len(version) != 4 or struct.unpack("!I", version)[0] != 1:
				raise IOError("Unknown version of storage file")
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
				raise IOError("Corrupted disk format - HMAC does not match or bad passphrase")
				
			serialized = self.decryptOuter(encrypted, self.outerIv)
			self.groups = cPickle.loads(serialized)
	
	def save(self, fname):
		"""
		Write password database to disk, encrypt it. Requires Trezor
		connected.
		
		@throws IOError: if writing file failed
		"""
		assert len(self.outerKey) == KEYSIZE
		rnd = Random.new()
		self.outerIv = rnd.read(BLOCKSIZE)
		wrappedKey = self.wrapKey(self.outerKey)
		
		with file(fname, "wb") as f:
			version = 1
			f.write(Magic.headerStr)
			f.write(struct.pack("!I", version))
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
		
	def encryptPassword(self, password, groupName):
		"""
		Encrypt a password. Does PKCS#5 padding before encryption. Inserts
		random block of data to sidestep IV issue in CipherKeyValue in
		Trezor.
		
		@param groupName key that will be shown to user on Trezor and
			used to encrypt the password. A string in utf-8
		"""
		rnd = Random.new()
		rndBlock = rnd.read(BLOCKSIZE)
		padded = Padding.pad(rndBlock + password)
		ugroup = groupName.decode("utf-8")
		ret = self.trezor.encrypt_keyvalue(Magic.groupNode, ugroup, padded, ask_on_encrypt=False, ask_on_decrypt=True)
		return ret
		
	def decryptPassword(self, encryptedPassword, groupName):
		"""
		Decrypt a password. After decryption strips PKCS#5 padding and
		discards first block.
		
		@param groupName key that will be shown to user on Trezor and
			was used to encrypt the password. A string in utf-8.
		"""
		ugroup = groupName.decode("utf-8")
		plain = self.trezor.decrypt_keyvalue(Magic.groupNode, ugroup, encryptedPassword, ask_on_encrypt=False, ask_on_decrypt=True)
		prefixed = Padding.unpad(plain)
		password = prefixed[BLOCKSIZE:]
		return password
		
		