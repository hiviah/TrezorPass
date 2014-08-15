#!/usr/bin/env python
import sys

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QApplication, QMainWindow, QMenu
#from PyQt4.QtCore import QSettings

from ui_mainwindow import Ui_MainWindow

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

class MainWindow(QMainWindow, Ui_MainWindow):
	"""Main window for the application with groups and password lists"""

	def __init__(self):
		QMainWindow.__init__(self)
		self.setupUi(self)
		
		self.addGroupMenu = QtGui.QMenu(self)
		self.addGroupMenu.addAction(QtGui.QAction('Add group', self))
		self.addGroupMenu.addAction(QtGui.QAction('Delete group', self))
		
		self.groupsTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.groupsTree.customContextMenuRequested.connect(self.groupsContextMenu)
	
	def groupsContextMenu(self, point):
		self.addGroupMenu.exec_(self.groupsTree.mapToGlobal(point))
		
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
print "label:", client.features.label

app = QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
sys.exit(app.exec_())
