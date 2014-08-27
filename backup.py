from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from password_map import Magic

class Backup(object):
	"""
	Performs backup and restore for password storage
	"""
	
	KEYSIZE = 2048
	
	def __init__(self):
		"""
		Create with no keys prepared.
		"""
		self.encryptedPrivate = None #encrypted private key
		self.publicKey = None
	
	def generate(self, trezor):
		"""
		Generate key and encrypt private key
		
		@param trezor: Trezor client object to use for encrypting private
			key
		"""
		key = RSA.generate(self.KEYSIZE)
		privateDer = key.exportKey(format="DER")
		self.publicKey = key.publickey()
		self.encryptedPrivate = trezor.encrypt_keyvalue(Magic.backupNode,
			Magic.backupKey, privateDer, ask_on_encrypt=False, ask_on_decrypt=True)