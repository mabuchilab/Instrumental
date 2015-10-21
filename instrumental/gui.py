import numpy as np
import scipy.misc
from PySide.QtCore import Qt, QLineF, QPointF, QTimer, Signal, QThread, QObject
from PySide.QtGui import *

mpl, FigureCanvas, Figure = None, None, None
def load_matplotlib():
    global mpl, FigureCanvas, Figure
    import matplotlib as mpl
    mpl.use('Qt4Agg')
    mpl.rcParams['backend.qt4'] = 'PySide'
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure


class MPLFigure:
    """Convenience class for adding MPL figures to PySide GUIs"""
    def __init__(self):
        if mpl is None:
            load_matplotlib()
        self.fig = Figure(tight_layout=True, frameon=False)
        self.canvas = FigureCanvas(self.fig)


class DrawableCameraView(QGraphicsView):
    overlay_changed = Signal()

    def __init__(self, camera=None, scene=None):
        super(DrawableCameraView, self).__init__()
        if scene is None:
            self.scene = QGraphicsScene()
        else:
            self.scene = scene
        self.setScene(self.scene)
        self.camera = camera
        self.pixmapitem = None

        # Overlay variables
        self.overlay_visible = False
        self.overlay_images = None

    def set_overlays(self, filenames):
        if not self.overlay_images:
            self.overlay_filenames = filenames
            self.overlay_images = [None] * len(filenames)
            self.overlay_index = len(filenames)  # Start at live video
        else:
            old_fnames = self.overlay_filenames
            old_images = self.overlay_images
            new_fnames = filenames
            new_images = [None] * len(new_fnames)

            for old_fname in old_fnames:
                i = new_fnames.index(old_fname)
                new_images[i] = old_images[i]

            self.overlay_filenames = new_fnames
            self.overlay_images = new_images
            self.overlay_index = len(filenames)

    def hide_overlay(self):
        if self.overlay_index < len(self.overlay_images):
            self.overlay_images[self.overlay_index].hide()
        self.overlay_visible = False

    def show_overlay(self):
        if self.overlay_index < len(self.overlay_images):
            self.overlay_images[self.overlay_index].show()
        self.overlay_visible = True

    def keyPressEvent(self, event):
        key = event.key()
        if self.overlay_visible and self.overlay_images is not None:
            # We have overlays active and visible
            if key == Qt.Key_Left:
                self.overlay_index -= 1
                if self.overlay_index < 0:
                    self.overlay_index = 0  # No wraparound
                else:
                    self.overlay_changed.emit()
                    if self.overlay_images[self.overlay_index] is None:
                        self._add_overlay_image()

                self.overlay_images[self.overlay_index].show()
                if self.overlay_index+1 < len(self.overlay_images):
                    self.overlay_images[self.overlay_index+1].hide()
            elif key == Qt.Key_Right:
                self.overlay_index += 1
                if self.overlay_index > len(self.overlay_images):
                    self.overlay_index = len(self.overlay_images)
                else:
                    if self.overlay_index < len(self.overlay_images):
                        self.overlay_images[self.overlay_index].show()
                    self.overlay_changed.emit()
                    self.overlay_images[self.overlay_index-1].hide()
        else:
            # Pass event through to base class
            QGraphicsView.keyPressEvent(self, event)

    def _add_overlay_image(self):
        fname = self.overlay_filenames[self.overlay_index]
        self.overlay_images[self.overlay_index] = self.scene.addPixmap(QPixmap(fname))
        self.overlay_images[self.overlay_index].setZValue(10000000)

    def start_video(self, framerate=None):
        timer = QTimer()
        timer.timeout.connect(self._wait_for_frame)
        self.camera.start_live_video(framerate)
        timer.start(int(1000/self.camera.framerate))
        self.timer = timer
        self.centerOn(self.camera.width/2, self.camera.height/2)

    def stop_video(self):
        self.camera.stop_live_video()
        self.timer.stop()

    def _wait_for_frame(self):
        if self.camera.wait_for_frame(0):
            data = self.camera.image_buffer()
            bpl = self.camera.bytes_per_line
            format = QImage.Format_RGB32
            image = QImage(data, self.camera.width, self.camera.height, bpl, format)
            if self.pixmapitem is None:
                self.pixmapitem = self.scene.addPixmap(QPixmap.fromImage(image))
            else:
                self.pixmapitem.setPixmap(QPixmap.fromImage(image))


class CameraView(QLabel):
    def __init__(self, camera=None):
        super(CameraView, self).__init__()
        self.camera = camera

    def grab_frame(self):
        self.camera.freeze_frame()
        self._set_pixmap_from_camera()

    def start_video(self, framerate=None):
        timer = QTimer()
        self.timer = timer
        timer.timeout.connect(self._wait_for_frame)
        self.camera.start_live_video(framerate)
        timer.start(int(1000./self.camera.framerate))

    def stop_video(self):
        self.timer.stop()
        self.camera.stop_live_video()

    def _set_pixmap_from_camera(self):
        bpl = self.camera.bytes_per_line
        arr = self.camera.image_array()

        if self.camera.color_mode == 'RGB32':
            buf = self.camera.image_buffer()  # TODO: Fix to use image_array() instead
            format = QImage.Format_RGB32
            image = QImage(buf, self.camera.width, self.camera.height, bpl, format)
        elif self.camera.color_mode == 'mono16':
            pil_img = scipy.misc.toimage(arr)  # Normalize values to fit in uint8
            format = QImage.Format_Indexed8
            data = pil_img.tostring()
            image = QImage(data, pil_img.size[0], pil_img.size[1], pil_img.size[0], format)
            self._saved_img = data  # Save a reference to keep Qt from crashing
        else:
            raise Exception("Unsupported color mode '{}'".format(self.camera.color_mode))

        self.setPixmap(QPixmap.fromImage(image))
        pixmap_size = self.pixmap().size()
        if pixmap_size != self.size():
            self.setMinimumSize(self.pixmap().size())

    def _wait_for_frame(self):
        frame_ready = self.camera.wait_for_frame(0)
        if frame_ready:
            self._set_pixmap_from_camera()

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
