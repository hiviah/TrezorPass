UI_GENERATED := \
    ui_mainwindow.py \
    ui_addgroup_dialog.py \
    #end of UI_GENERATED

all: $(UI_GENERATED)

ui_mainwindow.py: mainwindow.ui
	pyuic4 -o $@ $<

ui_addgroup_dialog.py: addgroup_dialog.ui
	pyuic4 -o $@ $<


