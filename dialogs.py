from PyQt4 import QtGui, QtCore

from ui_addgroup_dialog import Ui_AddGroupDialog
from ui_trezor_passphrase_dialog import Ui_TrezorPassphraseDialog
from ui_add_password_dialog import Ui_AddPasswordDialog

class AddGroupDialog(QtGui.QDialog, Ui_AddGroupDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
	
	def newGroupName(self):
		return self.newGroupEdit.text()
		
	
class TrezorPassphraseDialog(QtGui.QDialog, Ui_TrezorPassphraseDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
	
	def passphrase(self):
		return self.passphraseEdit.text()
		
	

class AddPasswordDialog(QtGui.QDialog, Ui_AddPasswordDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
	
	def key(self):
		return self.keyEdit.text()
		
	def pw1(self):
		return self.pwEdit1.text()
		
	def pw2(self):
		return self.pwEdit2.text()
		