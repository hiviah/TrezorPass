#!/usr/bin/env python
import sys
import os

from PyQt4 import QtGui, QtCore

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
		newGroupAction.triggered.connect(self.createGroup)
		deleteGroupAction = QtGui.QAction('Delete group', self)
		self.addGroupMenu.addAction(newGroupAction)
		self.addGroupMenu.addAction(deleteGroupAction)
		
		#disable deleting if no point is clicked on
		item = self.groupsTree.itemAt(point.x(), point.y())
		if item is None:
			deleteGroupAction.setEnabled(False)
		
		self.addGroupMenu.exec_(self.groupsTree.mapToGlobal(point))
			
	
	def showPasswdContextMenu(self, point):
		"""
		Show context menu for password management
		
		@param point: point in self.passwordTable where click occured
		"""
		self.passwdMenu = QtGui.QMenu(self)
		newItemAction = QtGui.QAction('New item', self)
		newItemAction.triggered.connect(self.createPassword)
		deleteItemAction = QtGui.QAction('Delete item', self)
		self.passwdMenu.addAction(newItemAction)
		self.passwdMenu.addAction(deleteItemAction)
		
		#disable deleting if no point is clicked on
		item = self.passwordTable.itemAt(point.x(), point.y())
		if item is None:
			deleteItemAction.setEnabled(False)
		
		self.passwdMenu.exec_(self.passwordTable.mapToGlobal(point))
	
	def createGroup(self):
		"""Slot to create a password group.
		"""
		dialog = AddGroupDialog()
		if not dialog.exec_():
			return
		
		groupName = dialog.newGroupName()
		if not groupName:
			return
		
		if str(groupName) in self.pwMap.groups:
			msgBox = QtGui.QMessageBox(text="Group already exists")
			msgBox.exec_()
			return
		
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
pwMap.outerIv = os.urandom(16)
pwMap.outerKey = os.urandom(32)
pwMap.encryptedBackupKey = ""

mainWindow = MainWindow(pwMap)
mainWindow.show()
retCode = app.exec_()

#pwMap.save("trezorpass.pwdb")
#pwMap.load("trezorpass.pwdb")

sys.exit(retCode)
