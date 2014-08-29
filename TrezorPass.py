#!/usr/bin/env python
import sys
import os.path

from PyQt4 import QtGui, QtCore
from Crypto import Random

from trezorlib.client import BaseClient, ProtocolMixin
from trezorlib.transport import ConnectionError
from trezorlib.transport_hid import HidTransport
from trezorlib import messages_pb2 as proto

from ui_mainwindow import Ui_MainWindow

import password_map
from encoding import q2s, s2q
from backup import Backup

from dialogs import AddGroupDialog, TrezorPassphraseDialog, AddPasswordDialog, \
	InitializeDialog

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
	"""Main window for the application with groups and password lists"""

	KEY_IDX = 0 #column where key is shown in password table
	PASSWORD_IDX = 1 #column where password is shown in password table
	CACHE_IDX = 0 #column of QWidgetItem in whose data we cache decrypted passwords
	
	def __init__(self, pwMap):
		QtGui.QMainWindow.__init__(self)
		self.setupUi(self)
		
		self.pwMap = pwMap
		self.selectedGroup = None
		
		self.groupsModel = QtGui.QStandardItemModel()
		self.groupsFilter = QtGui.QSortFilterProxyModel()
		self.groupsFilter.setSourceModel(self.groupsModel)
		
		self.groupsTree.setModel(self.groupsFilter)
		self.groupsTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.groupsTree.customContextMenuRequested.connect(self.showGroupsContextMenu)
		self.groupsTree.clicked.connect(self.loadPasswordsBySelection)
		self.groupsTree.selectionModel().selectionChanged.connect(self.loadPasswordsBySelection)
		self.groupsTree.setSortingEnabled(True)
		
		self.passwordTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.passwordTable.customContextMenuRequested.connect(self.showPasswdContextMenu)
		self.passwordTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self.passwordTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
		
		shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"), self.passwordTable, self.copyPasswordFromSelection)
		shortcut.setContext(QtCore.Qt.WidgetShortcut)
		
		self.actionQuit.triggered.connect(self.close)
		
		headerKey = QtGui.QTableWidgetItem("Key");
		headerValue = QtGui.QTableWidgetItem("Value");
		self.passwordTable.setColumnCount(2)
		self.passwordTable.setHorizontalHeaderItem(self.KEY_IDX, headerKey)
		self.passwordTable.setHorizontalHeaderItem(self.PASSWORD_IDX, headerValue)
		
		self.searchEdit.textChanged.connect(self.filterGroups)
		
		groupNames = self.pwMap.groups.keys()
		for groupName in groupNames:
			item = QtGui.QStandardItem(s2q(groupName))
			self.groupsModel.appendRow(item)
		self.groupsTree.sortByColumn(0, QtCore.Qt.AscendingOrder)
	
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
		proxyIdx = self.groupsTree.indexAt(point)
		itemIdx = self.groupsFilter.mapToSource(proxyIdx)
		item = self.groupsModel.itemFromIndex(itemIdx)
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
		copyPasswordAction.setShortcut(QtGui.QKeySequence( "Ctrl+C"))
		newItemAction = QtGui.QAction('New item', self)
		deleteItemAction = QtGui.QAction('Delete item', self)
		editItemAction = QtGui.QAction('Edit item', self)
		self.passwdMenu.addAction(showPasswordAction)
		self.passwdMenu.addAction(copyPasswordAction)
		self.passwdMenu.addSeparator()
		self.passwdMenu.addAction(newItemAction)
		self.passwdMenu.addAction(deleteItemAction)
		self.passwdMenu.addAction(editItemAction)
		
		#disable creating if no group is selected
		if self.selectedGroup is None:
			newItemAction.setEnabled(False)
		
		#disable deleting if no point is clicked on
		item = self.passwordTable.itemAt(point.x(), point.y())
		if item is None:
			deleteItemAction.setEnabled(False)
			showPasswordAction.setEnabled(False)
			copyPasswordAction.setEnabled(False)
			editItemAction.setEnabled(False)
		
		action = self.passwdMenu.exec_(self.passwordTable.mapToGlobal(point))
		if action == newItemAction:
			self.createPassword()
		elif action == deleteItemAction:
			self.deletePassword(item)
		elif action == showPasswordAction:
			self.showPassword(item)
		elif action == editItemAction:
			self.editPassword(item)
		elif action == copyPasswordAction:
			self.copyPasswordFromItem(item)
			
	
	def createGroup(self):
		"""Slot to create a password group.
		"""
		dialog = AddGroupDialog(self.pwMap.groups)
		if not dialog.exec_():
			return
		
		groupName = dialog.newGroupName()
		
		newItem = QtGui.QStandardItem(groupName)
		self.groupsModel.appendRow(newItem)
		self.pwMap.addGroup(q2s(groupName))
		
		#Make item's passwords loaded so new key-value pairs can be created
		#right away - better from UX perspective.
		self.loadPasswords(newItem)

		#make new item selected to save a few clicks
		itemIdx = self.groupsModel.indexFromItem(newItem)
		self.groupsTree.selectionModel().select(itemIdx,
			QtGui.QItemSelectionModel.ClearAndSelect | QtGui.QItemSelectionModel.Rows)
		self.groupsTree.sortByColumn(0, QtCore.Qt.AscendingOrder)
	
	def deleteGroup(self, item):
		msgBox = QtGui.QMessageBox(text="Are you sure about delete?")
		msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
		res = msgBox.exec_()
		
		if res != QtGui.QMessageBox.Yes:
			return
		
		name = q2s(item.text())
		self.selectedGroup = None
		del self.pwMap.groups[name]
		
		itemIdx = self.groupsModel.indexFromItem(item)
		self.groupsModel.takeRow(itemIdx.row())
		self.passwordTable.setRowCount(0)
		self.groupsTree.clearSelection()
	
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
		
		self.passwordTable.resizeRowsToContents()
	
	def cachePassword(self, row, password):
		"""
		Cache decrypted password for group and row. Cached items are
		keps as data of QTableWidgetItem so that deletion invalidates
		cache.
		
		Cache applies to currently selectedGroup.
		
		Switching between groups clears the table and thus invalidates
		cached passwords.
		"""
		item = self.passwordTable.item(row, MainWindow.CACHE_IDX)
		item.setData(QtCore.Qt.UserRole, QtCore.QVariant(s2q(password)))
	
	def cachedPassword(self, row):
		"""
		Retrieve cached password for given row of currently selected group.
		Returns password as string or None if no password cached.
		"""
		item = self.passwordTable.item(row, MainWindow.CACHE_IDX)
		cached = item.data(QtCore.Qt.UserRole)
		
		if cached.isValid():
			return q2s(cached.toString())
		
		return None
	
	def cachedOrDecrypt(self, row):
		"""
		Try retrieving cached password for item in given row, otherwise
		decrypt with Trezor.
		"""
		cached = self.cachedPassword(row)
		
		if cached is not None:
			return cached
		else: #decrypt with Trezor
			group = self.pwMap.groups[self.selectedGroup]
			pwPair = group.pair(row)
			encPw = pwPair[1]
			
			decrypted = self.pwMap.decryptPassword(encPw, self.selectedGroup)
		
		return decrypted
	
	def showPassword(self, item):
		#check if this password has been decrypted, use cached version
		row = self.passwordTable.row(item)
		decrypted = self.cachedOrDecrypt(row)
		item = QtGui.QTableWidgetItem(s2q(decrypted))
		
		self.cachePassword(row, decrypted)
		self.passwordTable.setItem(row, self.PASSWORD_IDX, item)
	
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
		self.passwordTable.setItem(rowCount, self.KEY_IDX, item)
		self.passwordTable.setItem(rowCount, self.PASSWORD_IDX, pwItem)
		
		plainPw = q2s(dialog.pw1())
		encPw = self.pwMap.encryptPassword(plainPw, self.selectedGroup)
		group.addPair(q2s(dialog.key()), encPw)
		
		self.cachePassword(rowCount, plainPw)
		
		self.passwordTable.resizeRowsToContents()
	
	def editPassword(self, item):
		row = self.passwordTable.row(item)
		group = self.pwMap.groups[self.selectedGroup]
		decrypted = self.cachedOrDecrypt(row)
		
		dialog = AddPasswordDialog()
		pair = group.pair(row)
		dialog.keyEdit.setText(s2q(pair[0]))
		dialog.pwEdit1.setText(s2q(decrypted))
		dialog.pwEdit2.setText(s2q(decrypted))
		
		if not dialog.exec_():
			return
		
		item = QtGui.QTableWidgetItem(dialog.key())
		pwItem = QtGui.QTableWidgetItem("*****")
		self.passwordTable.setItem(row, self.KEY_IDX, item)
		self.passwordTable.setItem(row, self.PASSWORD_IDX, pwItem)
		
		plainPw = q2s(dialog.pw1())
		encPw = self.pwMap.encryptPassword(plainPw, self.selectedGroup)
		group.updatePair(row, q2s(dialog.key()), encPw)
	
		self.cachePassword(row, plainPw)
		
	def copyPasswordFromSelection(self):
		"""
		Copy selected password to clipboard. Password is decrypted if
		necessary.
		"""
		indexes = self.passwordTable.selectedIndexes()
		if not indexes:
			return
		
		#there will be more indexes as the selection is on a row
		row = indexes[0].row()
		item = self.passwordTable.item(row, 1)
		self.copyPasswordFromItem(item)
	
	def copyPasswordFromItem(self, item):
		row = self.passwordTable.row(item)
		decrypted = self.cachedOrDecrypt(row)
		
		clipboard = QtGui.QApplication.clipboard()
		clipboard.setText(s2q(decrypted))
		
		self.cachePassword(row, decrypted)
		
	def loadPasswords(self, item):
		"""Slot that should load items for group that has been clicked on.
		"""
		#self.passwordTable.clear()
		name = q2s(item.text())
		self.selectedGroup = name
		group = self.pwMap.groups[name]
		self.passwordTable.setRowCount(len(group.pairs))
		self.passwordTable.setColumnCount(2)
		
		i = 0
		for key, encValue in group.pairs:
			item = QtGui.QTableWidgetItem(s2q(key))
			pwItem = QtGui.QTableWidgetItem("*****")
			self.passwordTable.setItem(i, self.KEY_IDX, item)
			self.passwordTable.setItem(i, self.PASSWORD_IDX, pwItem)
			i = i+1
		
		self.passwordTable.resizeRowsToContents()
	
	def loadPasswordsBySelection(self):
		proxyIdx = self.groupsTree.currentIndex()
		itemIdx = self.groupsFilter.mapToSource(proxyIdx)
		selectedItem = self.groupsModel.itemFromIndex(itemIdx)
		
		if not selectedItem:
			return
		
		self.loadPasswords(selectedItem)
	
	def filterGroups(self, substring):
		"""
		Filter groupsTree view to have items containing given substring.
		"""
		self.groupsFilter.setFilterFixedString(substring)
		self.groupsTree.sortByColumn(0, QtCore.Qt.AscendingOrder)
	
class QtTrezorMixin(object):
	"""
	Mixin for input of passhprases.
	"""
	
	def __init__(self, *args, **kwargs):
		super(QtTrezorMixin, self).__init__(*args, **kwargs)
		self.passphrase = None
	
	def callback_ButtonRequest(self, msg):
		return proto.ButtonAck()

	def callback_PassphraseRequest(self, msg):
		if self.passphrase is not None:
			return proto.PassphraseAck(passphrase=self.passphrase)
			
		dialog = TrezorPassphraseDialog()
		if not dialog.exec_():
			sys.exit(3)
		else:
			passphrase = dialog.passphraseEdit.text()
			passphrase = unicode(passphrase)
		
		return proto.PassphraseAck(passphrase=passphrase)
	
	def prefillPassphrase(self, passphrase):
		"""
		Instead of asking for passphrase, use this one
		"""
		self.passphrase = passphrase.decode("utf-8")

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
		

def initializeStorage(trezor, pwMap):
	"""
	Initialize new encrypted password file, ask for master passphrase.
	
	Initialize RSA keypair for backup, encrypt private RSA key using
	backup passphrase and Trezor's cipher-key-value system.
	
	Makes sure a session is created on Trezor so that the passphrase
	will be cached until disconnect.
	
	@param trezor: Trezor client
	@param pwMap: PasswordMap where to put encrypted backupKeys
	"""
	dialog = InitializeDialog()
	if not dialog.exec_():
		sys.exit(4)
		
	masterPassphrase = q2s(dialog.pw1())
	
	trezor.prefillPassphrase(masterPassphrase)
	backup = Backup(trezor)
	backup.generate()
	pwMap.backupKey = backup
	

app = QtGui.QApplication(sys.argv)

try:
	trezorChooser = TrezorChooser()
	trezorChooseCallback = lambda deviceTuples: 0
	trezor = trezorChooser.getDevice(trezorChooseCallback)
except ConnectionError:
	msgBox = QtGui.QMessageBox(text="Connection to Trezor failed")
	msgBox.exec_()
	sys.exit(1)
	

if trezor is None:
	msgBox = QtGui.QMessageBox(text="No available Trezor found, quitting.")
	msgBox.exec_()
	sys.exit(1)
	
trezor.clear_session()
#print "label:", trezor.features.label

pwMap = password_map.PasswordMap(trezor)

if os.path.isfile("trezorpass.pwdb"):
	try:
		pwMap.load("trezorpass.pwdb")
	except Exception, e:
		msgBox = QtGui.QMessageBox(text="Could not decrypt passwords: " + e.message)
		msgBox.exec_()
		sys.exit(5)
		
else:
	initializeStorage(trezor, pwMap)
	
rng = Random.new()
pwMap.outerIv = rng.read(password_map.BLOCKSIZE)
pwMap.outerKey = rng.read(password_map.KEYSIZE)
pwMap.encryptedBackupKey = ""

mainWindow = MainWindow(pwMap)
mainWindow.show()
retCode = app.exec_()

pwMap.save("trezorpass.pwdb")

sys.exit(retCode)
