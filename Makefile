all: ui_mainwindow.py

ui_mainwindow.py: mainwindow.ui
	pyuic4 -o $@ $<
