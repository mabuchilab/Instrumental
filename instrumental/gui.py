from PySide.QtCore import Qt, QLineF, QPointF, QTimer, Signal
from PySide.QtGui import QLabel, QImage, QPixmap, QGraphicsView, QGraphicsScene, QGraphicsLineItem, QPen, QBrush, QColor

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
            self.overlay_index = len(filenames) # Start at live video
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
                    self.overlay_index = 0 # No wraparound
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
            data = self.camera.get_image_buffer()
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
        timer.timeout.connect(self._wait_for_frame)
        self.camera.start_live_video(framerate)
        timer.start(int(1000/self.camera.framerate))
        self.timer = timer

    def stop_video(self):
        self.camera.stop_live_video()
        self.timer.stop()

    def _set_pixmap_from_camera(self):
        data = self.camera.get_image_buffer()
        bpl = self.camera.bytes_per_line
        format = QImage.Format_RGB32
        image = QImage(data, self.camera.width, self.camera.height, bpl, format)
        self.setPixmap(QPixmap.fromImage(image))

    def _wait_for_frame(self):
        if self.camera.wait_for_frame(0):
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
