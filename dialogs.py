from PyQt4 import QtGui, QtCore

from ui_addgroup_dialog import Ui_AddGroupDialog
from ui_trezor_passphrase_dialog import Ui_TrezorPassphraseDialog

class AddGroupDialog(QtGui.QDialog, Ui_AddGroupDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
	
	def newGroupName(self):
		return self.newGroupEdit.text()
		
	
class TrezorPassphraseDialog(QtGui.Dialog, Ui_TrezorPassphraseDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
	
	def passphrase(self):
		return self.passphraseEdit.text()
		
	
