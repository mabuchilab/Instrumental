# -*- coding: utf-8 -*-
# Copyright 2014-2016 Nate Bogdanowicz
import numpy as np
import scipy.misc
from .compat.QtCore import Qt, QTimer, Signal, QRect, QRectF, QPoint
from .compat.QtGui import (QPixmap, QImage, QLabel, QGraphicsView, QGraphicsScene, QFrame, QColor,
                           QPen, QMainWindow, QMouseEvent, QStyle, QPainter)
from .compat import PYSIDE

mpl, FigureCanvas, Figure = None, None, None
def load_matplotlib():
    global mpl, FigureCanvas, Figure
    import matplotlib as mpl
    mpl.use('Qt4Agg')
    if PYSIDE:
        mpl.rcParams['backend.qt4'] = 'PySide'
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure


class MPLFigure(object):
    """Convenience class for adding MPL figures to PySide/PyQt4 GUIs"""
    def __init__(self):
        if mpl is None:
            load_matplotlib()
        self.fig = Figure(tight_layout=True, frameon=False)
        self.canvas = FigureCanvas(self.fig)


class CameraView(QLabel):
    def __init__(self, camera=None):
        super(CameraView, self).__init__()
        self.camera = camera
        self._cmin = 0
        self._cmax = None

    def grab_image(self):
        arr = self.camera.grab_image()
        self._set_pixmap_from_array(arr)

    def start_video(self):
        timer = QTimer()
        self.timer = timer
        timer.timeout.connect(self._wait_for_frame)
        self.camera.start_live_video()
        timer.start(0)  # Run full throttle

    def stop_video(self):
        self.timer.stop()
        self.camera.stop_live_video()

    def _set_pixmap_from_array(self, arr):
        bpl = arr.strides[0]
        is_rgb = len(arr.shape) == 3

        if is_rgb and arr.dtype == np.uint8:
            format = QImage.Format_RGB32
            image = QImage(arr.data, self.camera.width, self.camera.height, bpl, format)
        elif not is_rgb and arr.dtype == np.uint8:
            # TODO: Somehow need to make sure data is ordered as I'm assuming
            format = QImage.Format_Indexed8
            image = QImage(arr.data, self.camera.width, self.camera.height, bpl, format)
            self._saved_img = arr
        elif not is_rgb and arr.dtype == np.uint16:
            if not self._cmax:
                self._cmax = arr.max()  # Set cmax once from first image
            arr = scipy.misc.bytescale(arr, self._cmin, self._cmax)
            format = QImage.Format_Indexed8
            w, h = self.camera.width, self.camera.height
            image = QImage(arr.data, w, h, w, format)
            self._saved_img = arr  # Save a reference to keep Qt from crashing
        else:
            raise Exception("Unsupported color mode")

        self.setPixmap(QPixmap.fromImage(image))
        pixmap_size = self.pixmap().size()
        if pixmap_size != self.size():
            self.setMinimumSize(self.pixmap().size())

    def _wait_for_frame(self):
        frame_ready = self.camera.wait_for_frame(timeout='0 ms')
        if frame_ready:
            arr = self.camera.latest_frame(copy=False)
            self._set_pixmap_from_array(arr)

    def set_height(self, h):
        """ Sets the height while keeping the image aspect ratio fixed """
        self.setScaledContents(True)
        cam = self.camera
        self.setFixedSize(cam.width*h/cam.height, h)

    def set_width(self, w):
        """ Sets the width while keeping the image aspect ratio fixed """
        self.setScaledContents(True)
        cam = self.camera
        self.setFixedSize(w, cam.height*w/cam.width)
