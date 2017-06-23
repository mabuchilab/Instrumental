# -*- coding: utf-8 -*-
# Copyright 2015-2017 Nate Bogdanowicz
"""
A very simple GUI that uses a CameraView to view live video from a camera.
"""
import sys
from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QScrollArea, QPushButton,
                            QVBoxLayout, QHBoxLayout)
from instrumental import instrument, gui


def create_window():
    # Create app and widgets
    app = QApplication(sys.argv)
    win = QMainWindow()
    main_area = QWidget()
    button_area = QWidget()
    scroll_area = QScrollArea()
    button = QPushButton("Start Video")
    btn_grab = QPushButton("Grab Frame")

    # Create layouts
    vbox = QVBoxLayout()
    hbox = QHBoxLayout()

    # Fill Layouts
    vbox.addWidget(scroll_area)
    vbox.addWidget(button_area)
    hbox.addStretch()
    hbox.addWidget(button)
    hbox.addWidget(btn_grab)

    # Assign layouts to widgets
    main_area.setLayout(vbox)
    button_area.setLayout(hbox)
    scroll_area.setLayout(QVBoxLayout())

    # Attach some child widgets directly
    win.setCentralWidget(main_area)

    return app, win, button, btn_grab, scroll_area


if __name__ == '__main__':
    cam = instrument('pxCam')  # Replace with your camera's alias

    with cam:
        app, win, ssbutton, btn_grab, scroll_area = create_window()
        camview = gui.CameraView(cam)
        scroll_area.setWidget(camview)

        ssbutton.running = False
        def start_stop():
            if not ssbutton.running:
                camview.start_video()
                ssbutton.setText("Stop Video")
                ssbutton.running = True
            else:
                camview.stop_video()
                ssbutton.setText("Start Video")
                ssbutton.running = False
        ssbutton.clicked.connect(start_stop)

        def grab():
            if not ssbutton.running:
                camview.grab_image()
        btn_grab.clicked.connect(grab)

        win.show()
        app.exec_()

        if ssbutton.running:
            camview.stop_video()
