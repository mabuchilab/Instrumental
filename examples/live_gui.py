"""
A GUI that can be used to view live video from two cameras simultaneously.
Also shows off image overlay capabilities: after you've toggled the overlay
button on, click on the main image to gain focus, then use the left and right
arrow keys to switch between overlay images.
"""

import sys
from PySide.QtGui import QApplication, QPushButton, QScrollArea, QHBoxLayout
from PySide.QtUiTools import QUiLoader

from instrumental.drivers.cameras import uc480
from instrumental import gui


if __name__ == '__main__':
    cam = uc480.get_camera(serial='4002856484')
    cam.open(num_bufs=2)
    cam.load_stored_parameters(1)

    cam2 = uc480.get_camera(serial='4002862589')
    cam2.open(num_bufs=2)
    cam2.load_stored_parameters(1)

    loader = QUiLoader()
    app = QApplication(sys.argv)
    ui = loader.load('live_gui.ui')

    scrollarea = ui.findChild(QScrollArea, 'scrollArea')
    camview = gui.DrawableCameraView(cam)
    scrollarea.setWidget(camview)

    camview2 = gui.CameraView(cam2)
    hbox = ui.findChild(QHBoxLayout, 'horizontalLayout')
    hbox.insertWidget(0, camview2)

    camview.set_overlays(['Side.jpg', 'Ruler.jpg', 'Top.jpg'])

    statusbar = ui.statusBar()
    def set_status():
        if not camview.overlay_visible \
                or camview.overlay_index >= len(camview.overlay_images):
            message = 'Live'
        else:
            message = camview.overlay_filenames[camview.overlay_index]
        statusbar.showMessage(message)
    camview.overlay_changed.connect(set_status)

    ssbutton = ui.findChild(QPushButton, 'startStopButton')
    def start_stop():
        if ssbutton.text() == "Start Video":
            camview.start_video()
            ssbutton.setText("Stop Video")
        else:
            camview.stop_video()
            ssbutton.setText("Start Video")
    ssbutton.clicked.connect(start_stop)

    ovbutton = ui.findChild(QPushButton, 'overlayButton')
    def toggle_overlay():
        if ovbutton.isChecked():
            camview.show_overlay()
        else:
            camview.hide_overlay()
        set_status()
    ovbutton.clicked.connect(toggle_overlay)

    start_stop()
    set_status()
    camview2.start_video()
    camview2.set_height(150)
    ui.show()
    app.exec_()

    camview.stop_video()
    cam.close()
