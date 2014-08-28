from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import AES
from Crypto import Random

from password_map import Magic, Padding

class Backup(object):
	"""
	Performs backup and restore for password storage
	"""
	
	RSA_KEYSIZE = 2048
	SYMMETRIC_KEYSIZE = 32
	BLOCKSIZE = 16

	
	def __init__(self, trezor):
		"""
		Create with no keys prepared.
		
		@param trezor: Trezor client object to use for encrypting private
			key
		"""
		self.encryptedPrivate = None #encrypted private key
		self.encryptedEphemeral = None #ephemeral key used to encrypt private RSA key
		self.ephemeralIv = None #IV used to encrypt private key with ephemeral key
		self.publicKey = None
		self.trezor = trezor
	
	def generate(self):
		"""
		Generate key and encrypt private key
		"""
		key = RSA.generate(self.RSA_KEYSIZE)
		privateDer = key.exportKey(format="DER")
		self.publicKey = key.publickey()
		self.wrapPrivateKey(privateDer)
		
	def wrapPrivateKey(self, privateKey):
		"""
		Wrap serialized private key by encrypting it with trezor.
		"""
		#Trezor client won't allow to encrypt whole serialized RSA key
		#in one go - it's too big. We need an ephemeral symmetric key
		#and encrypt the small ephemeral with Trezor.
		rng = Random.new()
		ephemeral = rng.read(self.SYMMETRIC_KEYSIZE)
		self.ephemeralIv = rng.read(self.BLOCKSIZE)
		cipher = AES.new(ephemeral, AES.MODE_CBC, self.ephemeralIv)
		padded = Padding.pad(privateKey)
		self.encryptedPrivate = cipher.encrypt(padded)
		
		self.encryptedEphemeral = self.trezor.encrypt_keyvalue(
			Magic.backupNode, Magic.backupKey, ephemeral,
			ask_on_encrypt=False, ask_on_decrypt=True)