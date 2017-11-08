# -*- coding: utf-8 -*-
# Copyright 2014-2016 Nate Bogdanowicz
import numpy as np
import scipy.misc
from qtpy.QtCore import Qt, QTimer, Signal, QRect, QRectF, QPoint
from qtpy.QtGui import QPixmap, QImage, QColor, QPen, QMouseEvent, QPainter
from qtpy.QtWidgets import QGraphicsView, QGraphicsScene, QMainWindow, QLabel, QStyle
from qtpy import PYSIDE, PYQT5

mpl, FigureCanvas, Figure = None, None, None
def load_matplotlib():
    global mpl, FigureCanvas, Figure
    import matplotlib as mpl
    if PYQT5:
        mpl.use('Qt5Agg')
    else:
        mpl.use('Qt4Agg')

    if PYSIDE:
        mpl.rcParams['backend.qt4'] = 'PySide'

    if PYQT5:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    else:
        from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

    from matplotlib.figure import Figure


class MPLFigure(object):
    """Convenience class for adding MPL figures to PySide/PyQt4 GUIs"""
    def __init__(self):
        if mpl is None:
            load_matplotlib()
        self.fig = Figure(tight_layout=True, frameon=False)
        self.canvas = FigureCanvas(self.fig)


def create_figure_window(title=''):
    """Creates a figure in a Qt window. Returns the tuple (window, mplfigure)"""
    win = QMainWindow()
    mplfig = MPLFigure()
    win.setCentralWidget(mplfig.canvas)
    win.setWindowTitle(title)
    return win, mplfig


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


class CroppableCameraView(QGraphicsView):
    rectChanged = Signal(QRect)
    imageDisplayed = Signal(np.ndarray)
    videoStarted = Signal()
    mouseMoved = Signal(QMouseEvent)
    mousePressed = Signal(QMouseEvent)
    mouseReleased = Signal(QMouseEvent)

    def __init__(self, camera, **settings):
        super(CroppableCameraView, self).__init__()
        self.setRenderHint(QPainter.Antialiasing)
        self.cam = camera
        self.is_live = False
        self._cmin = 0
        self._cmax = None
        self.settings = settings
        self._selecting = False
        self.needs_resize = False
        self.latest_array = None

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene()
        #self.setFrameStyle(QFrame.NoFrame)
        self.setScene(self.scene)
        self.pixmapitem = self.scene.addPixmap(QPixmap())
        self._uncropped_pixmap = None

        self.setMouseTracking(True)

        self.start = None
        c1 = QColor(0, 100, 220, 150)
        self.c2 = QColor(0, 100, 220, 50)
        self.c3 = QColor(0, 100, 220, 0)
        pen = QPen(c1, 2)

        self.selrect = self.scene.addRect(1, 1, 1, 1, pen, self.c3)
        self.selrect.setZValue(100)
        self.selrect.hide()

    def enable_selecting(self):
        print("Selection enabled")
        self._selecting = True

    def disable_selecting(self):
        self._selecting = False

    def mousePressEvent(self, event):
        if self._selecting:
            print("Mouse pressed")
            if not self.selrect.isVisible():
                self.selrect.show()

            if event.button() == Qt.LeftButton:
                sp = self.mapToScene(event.pos())
                self.start = (sp.x(), sp.y())
                self.selrect.setRect(sp.x(), sp.y(), 0, 0)
                self.selrect.setBrush(self.c2)

        self.mousePressed.emit(event)

    def mouseMoveEvent(self, event):
        if self.start:
            x1, y1 = self.start
            sp = self.mapToScene(event.pos())

            # Image width, height in scene coords
            ir = self.pixmapitem.boundingRect()
            sr = self.pixmapitem.sceneTransform().mapRect(ir)

            size = self.pixmapitem.pixmap().size()
            x2 = max(sr.left(), min(sr.right()-1, sp.x()))
            y2 = max(sr.top(), min(sr.bottom()-1, sp.y()))
            x1, x2 = sorted((x1, x2))
            y1, y2 = sorted((y1, y2))
            self.selrect.setRect(x1, y1, x2-x1, y2-y1)

        self.mouseMoved.emit(event)

    def mouseReleaseEvent(self, event):
        if self.start and event.button() == Qt.LeftButton:
            self.start = None
            self.selrect.setBrush(self.c3)
            self.rectChanged.emit(self.selrect.rect().toRect())

        self.mouseReleased.emit(event)

    def update_rect(self, x, y, w, h):
        self.selrect.setRect(x, y, w, h)
        self.rectChanged.emit(self.selrect.rect().toRect())

    def hideRect(self):
        self.selrect.hide()

    def showRect(self):
        self.selrect.show()

    def setRectVisible(self, visible):
        self.selrect.setVisible(visible)

    def isRectVisible(self):
        return self.selrect.isVisible()

    def rect(self):
        """QRect of the selection in camera coordinates"""
        # selrect in _image_ (pixmap) coordinates
        i_selrect = self.pixmapitem.sceneTransform().inverted()[0].mapRect(self.selrect.rect())
        current_left = self.settings.get('left', 0)
        current_top = self.settings.get('top', 0)
        return i_selrect.toRect().translated(current_left, current_top)

    def crop_to_rect(self):
        was_live = self.is_live
        if was_live:
            self.stop_video()

        self.hideRect()

        rect = self.rect()
        self.settings['left'] = rect.left()
        self.settings['right'] = rect.right()
        self.settings['top'] = rect.top()
        self.settings['bot'] = rect.bottom()

        if was_live:
            self.start_video()
        else:
            if not self._uncropped_pixmap:
                self._uncropped_pixmap = self.pixmapitem.pixmap()
            self.pixmapitem.setPixmap(self._uncropped_pixmap.copy(rect))
            self.setFixedSize(rect.width(), rect.height())

    def uncrop(self):
        was_live = self.is_live
        if was_live:
            self.stop_video()

        for key in ['left', 'right', 'top', 'bot']:
            if key in self.settings:
                del self.settings[key]

        if was_live:
            self.start_video()
        else:
            pixmap = self._uncropped_pixmap
            self.pixmapitem.setPixmap(pixmap)

        ir = self.pixmapitem.boundingRect()
        sr = self.pixmapitem.sceneTransform().mapRect(ir)
        self.scene.setSceneRect(sr)
        self.setFixedSize(sr.width(), sr.height())

    def mapSceneToPixmap(self, pt):
        transform = self.pixmapitem.sceneTransform().inverted()[0]
        return transform.mapRect(pt) if isinstance(pt, (QRect, QRectF)) else transform.map(pt)

    def mapViewToPixmap(self, view_pt):
        scene_pt = self.mapToScene(view_pt)
        return self.mapSceneToPixmap(scene_pt)

    def mapPixmapToScene(self, pixmap_pt):
        transform = self.pixmapitem.sceneTransform()
        map_func = transform.mapRect if isinstance(pixmap_pt, (QRect, QRectF)) else transform.map
        return map_func(pixmap_pt)

    def mapSceneToCamera(self, sc_pt):
        px_pt = self.mapSceneToPixmap(sc_pt)
        return QPoint(px_pt.x() + self.settings.get('left', 0),
                      px_pt.y() + self.settings.get('top', 0))

    def set_image(self, image_arr):
        pixmap = QPixmap(self._array_to_qimage(image_arr))
        if not self.pixmapitem:
            self.pixmapitem = self.scene.addPixmap(pixmap)
        else:
            self.pixmapitem.setPixmap(pixmap)

        if self.needs_resize:
            self._autoresize_viewport()
            self.needs_resize = False

    def _autoresize_viewport(self):
        ir = self.pixmapitem.boundingRect()
        sr = self.pixmapitem.sceneTransform().mapRect(ir)
        self.scene.setSceneRect(sr)
        #self.setFixedSize(sr.width(), sr.height())
        self.resize(sr.width(), sr.height())
        #self.viewport().setMaximumSize(sr.width(), sr.height())
        d = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self.setMaximumSize(sr.width() + 2*d, sr.height() + 2*d)

    def grab_image(self):
        arr = self.cam.grab_image(**self.settings)
        self.set_image(arr)
        self.latest_array = arr
        self.imageDisplayed.emit(arr)

    def start_video(self):
        timer = QTimer()
        self.timer = timer
        timer.timeout.connect(self._wait_for_frame)
        self.cam.start_live_video(**self.settings)
        timer.start(0)  # Run full throttle
        self.is_live = True
        self.needs_resize = True
        self.videoStarted.emit()

    def stop_video(self):
        self.timer.stop()
        self.cam.stop_live_video()
        self.is_live = False

    def _wait_for_frame(self):
        frame_ready = self.cam.wait_for_frame(timeout='0 ms')
        if frame_ready:
            arr = self.cam.latest_frame(copy=True)
            self.set_image(arr)
            self.latest_array = arr
            self.imageDisplayed.emit(arr)

    def _scale_image(self, arr):
        """Return a bytescaled copy of the image array"""
        if not self._cmax:
            self._cmax = arr.max()  # Set cmax once from first image
        return scipy.misc.bytescale(arr, self._cmin, self._cmax)

    def _lut_scale_image(self, arr):
        if not self._cmax:
            self._cmax = arr.max()
        lut = scipy.misc.bytescale(np.arange(2**16), self._cmin, self._cmax)
        return lut[arr]

    def _create_lut(self, k):
        A = 2**15
        B = 100  # k's scaling factor
        g = lambda i, k: A*((k-B)*i) / ((2*k)*x - (k+B)*A)

    def _array_to_qimage(self, arr):
        bpl = arr.strides[0]
        is_rgb = len(arr.shape) == 3

        if is_rgb and arr.dtype == np.uint8:
            format = QImage.Format_RGB32
            image = QImage(arr.data, self.cam.width, self.cam.height, bpl, format)
        elif not is_rgb and arr.dtype == np.uint8:
            # TODO: Somehow need to make sure data is ordered as I'm assuming
            format = QImage.Format_Indexed8
            image = QImage(arr.data, self.cam.width, self.cam.height, bpl, format)
            self._saved_img = arr
        elif not is_rgb and arr.dtype == np.uint16:
            arr = self._scale_image(arr)
            format = QImage.Format_Indexed8
            w, h = self.cam.width, self.cam.height
            image = QImage(arr.data, w, h, w, format)
            self._saved_img = arr  # Save a reference to keep Qt from crashing
        else:
            raise Exception("Unsupported color mode")

        return image
