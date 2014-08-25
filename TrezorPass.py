#!/usr/bin/env python
import sys

from PyQt4 import QtGui, QtCore
from Crypto import Random

from trezorlib.client import BaseClient, ProtocolMixin
from trezorlib.transport_hid import HidTransport
from trezorlib import messages_pb2 as proto

from ui_mainwindow import Ui_MainWindow

import password_map

from dialogs import AddGroupDialog, TrezorPassphraseDialog, AddPasswordDialog

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
	"""Main window for the application with groups and password lists"""

	def __init__(self, pwMap):
		QtGui.QMainWindow.__init__(self)
		self.setupUi(self)
		
		self.pwMap = pwMap
		self.selectedGroup = None
		
		self.groupsTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.groupsTree.customContextMenuRequested.connect(self.showGroupsContextMenu)
		self.groupsTree.itemClicked.connect(self.loadPasswords)
		self.groupsTree.itemSelectionChanged.connect(self.loadPasswordsBySelection)
		
		self.passwordTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.passwordTable.customContextMenuRequested.connect(self.showPasswdContextMenu)
		
		headerKey = QtGui.QTableWidgetItem("Key");
		headerValue = QtGui.QTableWidgetItem("Value");
		self.passwordTable.setColumnCount(2)
		self.passwordTable.setHorizontalHeaderItem(0, headerKey)
		self.passwordTable.setHorizontalHeaderItem(1, headerValue)
		
	
	def showGroupsContextMenu(self, point):
		"""
		Show context menu for group management.
		
		@param point: point in self.groupsTree where click occured
		"""
		self.addGroupMenu = QtGui.QMenu(self)
		newGroupAction = QtGui.QAction('Add group', self)
		deleteGroupAction = QtGui.QAction('Delete group', self)
		self.addGroupMenu.addAction(newGroupAction)
		self.addGroupMenu.addAction(deleteGroupAction)
		
		#disable deleting if no point is clicked on
		item = self.groupsTree.itemAt(point.x(), point.y())
		if item is None:
			deleteGroupAction.setEnabled(False)
		
		action = self.addGroupMenu.exec_(self.groupsTree.mapToGlobal(point))
		
		if action == newGroupAction:
			self.createGroup()
		elif action == deleteGroupAction:
			self.deleteGroup(item)
			
	
	def showPasswdContextMenu(self, point):
		"""
		Show context menu for password management
		
		@param point: point in self.passwordTable where click occured
		"""
		self.passwdMenu = QtGui.QMenu(self)
		showPasswordAction = QtGui.QAction('Show password', self)
		copyPasswordAction = QtGui.QAction('Copy password', self)
		newItemAction = QtGui.QAction('New item', self)
		deleteItemAction = QtGui.QAction('Delete item', self)
		self.passwdMenu.addAction(showPasswordAction)
		self.passwdMenu.addAction(copyPasswordAction)
		self.passwdMenu.addSeparator()
		self.passwdMenu.addAction(newItemAction)
		self.passwdMenu.addAction(deleteItemAction)
		
		#disable creating if no group is selected
		if self.selectedGroup is None:
			newItemAction.setEnabled(False)
		
		#disable deleting if no point is clicked on
		item = self.passwordTable.itemAt(point.x(), point.y())
		if item is None:
			deleteItemAction.setEnabled(False)
			showPasswordAction.setEnabled(False)
			copyPasswordAction.setEnabled(False)
		
		action = self.passwdMenu.exec_(self.passwordTable.mapToGlobal(point))
		if action == newItemAction:
			self.createPassword()
		elif action == deleteItemAction:
			self.deletePassword(item)
		elif action == showPasswordAction:
			self.showPassword(item)
			
	
	def createGroup(self):
		"""Slot to create a password group.
		"""
		dialog = AddGroupDialog(self.pwMap.groups)
		if not dialog.exec_():
			return
		
		groupName = dialog.newGroupName()
		
		newItem = QtGui.QTreeWidgetItem([groupName])
		self.groupsTree.addTopLevelItem(newItem)
		self.pwMap.addGroup(groupName)
		
		#Make item's passwords loaded so new key-value pairs can be created
		#right away - better from UX perspective.
		self.loadPasswords(newItem)

		#make new item selected to save a few clicks
		itemIdx = self.groupsTree.indexFromItem(newItem)
		self.groupsTree.selectionModel().select(itemIdx,
			QtGui.QItemSelectionModel.ClearAndSelect | QtGui.QItemSelectionModel.Rows)
	
	def deletePassword(self, item):
		msgBox = QtGui.QMessageBox(text="Are you sure about delete?")
		msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
		res = msgBox.exec_()
		
		if res != QtGui.QMessageBox.Yes:
			return
		
		row = self.passwordTable.row(item)
		self.passwordTable.removeRow(row)
		group = self.pwMap.groups[self.selectedGroup]
		group.removePair(row)
	
	def showPassword(self, item):
		#check if this password has been decrypted, use cached version
		row = self.passwordTable.row(item)
		cached = item.data(QtCore.Qt.UserRole)
		
		if cached.isValid():
			decrypted = str(cached.toString())
		else: #decrypt with Trezor
			
			group = self.pwMap.groups[self.selectedGroup]
			pwPair = group.pair(row)
			encPw = pwPair[1]
			
			decrypted = self.pwMap.decryptPassword(encPw, self.selectedGroup)
		item = QtGui.QTableWidgetItem(decrypted)
		
		#cache already decrypted password until table is refreshed
		item.setData(QtCore.Qt.UserRole, QtCore.QVariant(decrypted))
		self.passwordTable.item(row, 0).setData(QtCore.Qt.UserRole, QtCore.QVariant(decrypted))
		self.passwordTable.setItem(row, 1, item)
	
	def deleteGroup(self, item):
		name = str(item.text(0))
		self.selectedGroup = None
		del self.pwMap.groups[name]
		
		itemIdx = self.groupsTree.indexOfTopLevelItem(item)
		self.groupsTree.takeTopLevelItem(itemIdx)
		self.passwordTable.setRowCount(0)
	
	def createPassword(self):
		"""Slot to create key-value password pair.
		"""
		if self.selectedGroup is None:
			return
		group = self.pwMap.groups[self.selectedGroup]
		dialog = AddPasswordDialog()
		if not dialog.exec_():
			return
		
		rowCount = self.passwordTable.rowCount()
		self.passwordTable.setRowCount(rowCount+1)
		item = QtGui.QTableWidgetItem(dialog.key())
		pwItem = QtGui.QTableWidgetItem("*****")
		self.passwordTable.setItem(rowCount, 0, item)
		self.passwordTable.setItem(rowCount, 1, pwItem)
		
		plainPw = str(dialog.pw1())
		encPw = self.pwMap.encryptPassword(plainPw, self.selectedGroup)
		group.addPair(str(dialog.key()), encPw)
	
	def loadPasswords(self, item):
		"""Slot that should load items for group that has been clicked on.
		"""
		#self.passwordTable.clear()
		name = str(item.text(0))
		self.selectedGroup = name
		group = self.pwMap.groups[name]
		self.passwordTable.setRowCount(len(group.pairs))
		self.passwordTable.setColumnCount(2)
		
		i = 0
		for key, encValue in group.pairs:
			item = QtGui.QTableWidgetItem(key)
			pwItem = QtGui.QTableWidgetItem("*****")
			self.passwordTable.setItem(i, 0, item)
			self.passwordTable.setItem(i, 1, pwItem)
			i = i+1
	
	def loadPasswordsBySelection(self):
		selectedItems = self.groupsTree.selectedItems()
		
		if len(selectedItems) < 1:
			return
		
		item = selectedItems[0]
		self.loadPasswords(item)
	
class QtTrezorMixin(object):
	"""
	Mixin for input of passhprases.
	"""
	
	def __init__(self, *args, **kwargs):
		super(QtTrezorMixin, self).__init__(*args, **kwargs)
	
	def callback_ButtonRequest(self, msg):
		return proto.ButtonAck()

	def callback_PassphraseRequest(self, msg):
		dialog = TrezorPassphraseDialog()
		if not dialog.exec_():
			sys.exit(3)
		else:
			passphrase = dialog.passphraseEdit.text()
			passphrase = unicode(passphrase)
		
		return proto.PassphraseAck(passphrase=passphrase)

class QtTrezorClient(ProtocolMixin, QtTrezorMixin, BaseClient):
	"""
	Trezor client with Qt input methods
	"""
	pass

class TrezorChooser(object):
	"""Class for working with Trezor device via HID"""
	
	def __init__(self):
		pass
	
	def getDevice(self, callback):
		"""
		Get one from available devices. Callback chooses index
		of device, see chooseDevice callback.
		"""
		devices = self.enumerateHIDDevices()

		if not devices:
			return None
		
		transport = self.chooseDevice(devices, callback)
		client = QtTrezorClient(transport)

		return client

	def enumerateHIDDevices(self):
		"""Returns Trezor HID devices"""
		devices = HidTransport.enumerate()

		return devices

	def chooseDevice(self, devices, callback):
		"""
		Choose device from enumerated list. Callback gets list of
		tuples (index, string) which denote labels of connected trezors.
		The callback returns index of device that should be used.
		"""
		if not len(devices):
			raise RuntimeError("No Trezor connected!")

		if len(devices) == 1:
			try:
				return HidTransport(devices[0])
			except IOError:
				raise RuntimeError("Trezor is currently in use")
		
		deviceTuples = []
		
		for idx, device in enumerate(devices):
			try:
				transport = HidTransport(devices[0])
				client = QtTrezorClient(transport)
				label = client.features.label and client.features.label or "<no label>"
				deviceTuples += [(idx, label)]
			except IOError:
				#device in use, do not offer as choice
				continue
				
		if not deviceTuples:
			raise RuntimeError("All connected Trezors are in use!")
		
		chosenDevice = callback(deviceTuples)
		return deviceTuples[chosenDevice][1]
		


app = QtGui.QApplication(sys.argv)

trezorChooser = TrezorChooser()
trezorChooseCallback = lambda deviceTuples: 0
trezor = trezorChooser.getDevice(trezorChooseCallback)

if trezor is None:
	msgBox = QtGui.QMessageBox(text="No available Trezor found, quitting.")
	msgBox.exec_()
	sys.exit(1)
	
trezor.clear_session()
#print "label:", trezor.features.label

pwMap = password_map.PasswordMap(trezor)
#pwMap.load("trezorpass.pwdb")
rng = Random.new()
pwMap.outerIv = rng.read(password_map.BLOCKSIZE)
pwMap.outerKey = rng.read(password_map.KEYSIZE)
pwMap.encryptedBackupKey = ""

mainWindow = MainWindow(pwMap)
mainWindow.show()
retCode = app.exec_()

#pwMap.save("trezorpass.pwdb")
#pwMap.load("trezorpass.pwdb")

sys.exit(retCode)
