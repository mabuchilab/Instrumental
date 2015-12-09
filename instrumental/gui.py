import scipy.misc
from PySide.QtCore import Qt, QTimer, Signal
from PySide.QtGui import QGraphicsView, QGraphicsScene, QPixmap, QImage, QLabel

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
        elif self.camera.color_mode == 'mono8':
            # TODO: Somehow need to make sure data is ordered as I'm assuming
            format = QImage.Format_Indexed8
            image = QImage(arr.data, self.camera.width, self.camera.height, bpl, format)
            self._saved_img = arr
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
