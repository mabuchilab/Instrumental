"""
A simple GUI that can grab snapshots from a uc480 camera plugged
into the local machine. Cameras currently only support Windows.
"""

import sys
from PySide.QtGui import QApplication, QScrollArea, QPushButton
from PySide.QtUiTools import QUiLoader

from instrumental.drivers.cameras import uc480
from instrumental import gui

if __name__ == '__main__':
    # Change serial number to match that of your camera
    cam = uc480.get_camera(serial='4002862589')
    cam.open()
    cam.load_stored_parameters(1) # Load camera's stored parameters (optional)

    # Load Qt and the UI file
    loader = QUiLoader()
    app = QApplication(sys.argv)
    ui = loader.load('snapshot_gui.ui')

    # Create and add CameraView to the GUI's scrollarea
    cam_view = gui.CameraView(cam)
    scroll_area = ui.findChild(QScrollArea, 'scrollArea')
    scroll_area.setWidget(cam_view)

    # Grab a frame whenever the button is pushed
    button = ui.findChild(QPushButton, 'acquireButton')
    button.clicked.connect(cam_view.grab_frame)

    # Show the window and enter the GUI's main loop
    ui.show()
    app.exec_()

    # Clean up once we're done
    cam.close()
