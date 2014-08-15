#!/usr/bin/env python
import sys

from PyQt4.QtGui import QApplication, QMainWindow
from ui_mainwindow import Ui_MainWindow

class MainWindow(QMainWindow, Ui_MainWindow):
	"""Main window for the application with groups and password lists"""

	def __init__(self):
		QMainWindow.__init__(self)
		self.setupUi(self)

app = QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
sys.exit(app.exec_())
