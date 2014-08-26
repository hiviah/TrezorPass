from PyQt4 import QtGui, QtCore

from ui_addgroup_dialog import Ui_AddGroupDialog
from ui_trezor_passphrase_dialog import Ui_TrezorPassphraseDialog
from ui_add_password_dialog import Ui_AddPasswordDialog
from ui_initialize_dialog import Ui_InitializeDialog

class AddGroupDialog(QtGui.QDialog, Ui_AddGroupDialog):
	
	def __init__(self, groups):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
		self.newGroupEdit.textChanged.connect(self.validate)
		self.groups = groups
		
		#disabled for empty string
		button = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
		button.setEnabled(False)
	
	def newGroupName(self):
		return self.newGroupEdit.text()
		
	
	def validate(self):
		"""
		Validates input if name is not empty and is different from
		existing group names.
		"""
		valid = True
		text = self.newGroupEdit.text()
		if text.isEmpty():
			valid = False
		
		if str(text) in self.groups:
			valid = False
		
		button = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
		button.setEnabled(valid)
	
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
		self.pwEdit1.textChanged.connect(self.validatePw)
		self.pwEdit2.textChanged.connect(self.validatePw)
		self.showHideButton.clicked.connect(self.switchPwVisible)
	
	def key(self):
		return self.keyEdit.text()
	
	def pw1(self):
		return self.pwEdit1.text()
	
	def pw2(self):
		return self.pwEdit2.text()
	
	def validatePw(self):
		same = self.pw1() == self.pw2()
		button = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
		button.setEnabled(same)
	
	def switchPwVisible(self):
		pwMode = self.pwEdit1.echoMode()
		if pwMode == QtGui.QLineEdit.Password:
			newMode = QtGui.QLineEdit.Normal
		else:
			newMode = QtGui.QLineEdit.Password
			
		self.pwEdit1.setEchoMode(newMode)
		self.pwEdit2.setEchoMode(newMode)
		
class InitializeDialog(QtGui.QDialog, Ui_InitializeDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
		self.masterEdit1.textChanged.connect(self.validatePw)
		self.masterEdit2.textChanged.connect(self.validatePw)
	
	
	def pw1(self):
		return self.masterEdit1.text()
	
	def pw2(self):
		return self.masterEdit2.text()
	
	def validatePw(self):
		same = self.pw1() == self.pw2()
		button = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
		button.setEnabled(same)