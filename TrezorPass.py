#!/usr/bin/env python
import sys

from PyQt4.QtGui import QApplication, QMainWindow
from ui_mainwindow import Ui_MainWindow

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

class MainWindow(QMainWindow, Ui_MainWindow):
	"""Main window for the application with groups and password lists"""

	def __init__(self):
		QMainWindow.__init__(self)
		self.setupUi(self)

class Trezor(object):
	"""Class for working with Trezor device via HID"""
	
	def getDevice(self):
		"""Get one from available devices"""
		devices = self.enumerateHIDDevices()

		if not devices:
			return None
		
		transport = self.chooseDevice(devices)
		client = TrezorClient(transport)

		return client

	def enumerateHIDDevices(self):
		devices = HidTransport.enumerate()

		return devices

	def chooseDevice(self, devices):
		if not len(devices):
			raise Exception("No Trezor connected!")

		# always tries the one it finds
		try:
			return HidTransport(devices[0])
		except IOError:
			raise Exception("Device is currently in use")


trezor = Trezor()
client = trezor.getDevice()
print client

app = QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
sys.exit(app.exec_())
