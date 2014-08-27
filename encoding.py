from PyQt4 import QtCore

def q2s(s):
	"""Convert QString to UTF-8 string object"""
	return str(s.toUtf8())

def s2q(s):
	"""Convert UTF-8 encoded string to QString"""
	return QtCore.QString.fromUtf8(s)
