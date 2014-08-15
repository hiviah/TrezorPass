#!/usr/bin/env python
import sys

from PyQt4 import QtGui, QtCore

from ui_mainwindow import Ui_MainWindow
from ui_addgroup_dialog import Ui_AddGroupDialog

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

class AddGroupDialog(QtGui.QDialog, Ui_AddGroupDialog):
	
	def __init__(self):
		QtGui.QDialog.__init__(self)
		self.setupUi(self)
	
	def newGroupName(self):
		return self.newGroupEdit.text()
		
class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
	"""Main window for the application with groups and password lists"""

	def __init__(self):
		QtGui.QMainWindow.__init__(self)
		self.setupUi(self)
		
		self.groupsTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.groupsTree.customContextMenuRequested.connect(self.showGroupsContextMenu)
		
		self.passwordTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.passwordTable.customContextMenuRequested.connect(self.showPasswdContextMenu)
		
		header0 = QtGui.QTableWidgetItem("");
		header1 = QtGui.QTableWidgetItem("Key");
		header2 = QtGui.QTableWidgetItem("Value");
		self.passwordTable.setColumnCount(3)
		self.passwordTable.setHorizontalHeaderItem(0, header0)
		self.passwordTable.setHorizontalHeaderItem(1, header1)
		self.passwordTable.setHorizontalHeaderItem(2, header2)
		
	
	def showGroupsContextMenu(self, point):
		self.addGroupMenu = QtGui.QMenu(self)
		newGroupAction = QtGui.QAction('Add group', self)
		newGroupAction.triggered.connect(self.createGroup)
		deleteGroupAction = QtGui.QAction('Delete group', self)
		self.addGroupMenu.addAction(newGroupAction)
		self.addGroupMenu.addAction(deleteGroupAction)
		
		action = self.addGroupMenu.exec_(self.groupsTree.mapToGlobal(point))
			
	
	def showPasswdContextMenu(self, point):
		self.passwdMenu = QtGui.QMenu(self)
		newItemAction = QtGui.QAction('New item', self)
		deleteItemAction = QtGui.QAction('Delete item', self)
		self.passwdMenu.addAction(newItemAction)
		self.passwdMenu.addAction(deleteItemAction)
		
		self.passwdMenu.exec_(self.passwordTable.mapToGlobal(point))
	
	def createGroup(self):
		dialog = AddGroupDialog()
		if not dialog.exec_():
			return
		
		groupName = dialog.newGroupName()
		newItem = QtGui.QTreeWidgetItem([groupName])
		self.groupsTree.addTopLevelItem(newItem)
	
class Trezor(object):
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
		client = TrezorClient(transport)

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
				client = TrezorClient(transport)
				label = client.features.label and client.features.label or "<no label>"
				deviceTuples += [(idx, label)]
			except IOError:
				#device in use, do not offer as choice
				continue
				
		if not deviceTuples:
			raise RuntimeError("All connected Trezors are in use!")
		
		chosenDevice = callback(deviceTuples)
		return deviceTuples[chosenDevice][1]
		


trezor = Trezor()
trezorChooseCallback = lambda deviceTuples: 0
client = trezor.getDevice(trezorChooseCallback)
#print "label:", client.features.label

app = QtGui.QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
sys.exit(app.exec_())
