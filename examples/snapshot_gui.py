import sys
from ctypes import cast, c_char, POINTER
from PySide.QtGui import QApplication, QLabel, QPushButton, QImage, QPixmap
from PySide.QtUiTools import QUiLoader

from instrumental.drivers.cameras import uc480

loader = QUiLoader()

def get_image(cam):
    cam.freeze_frame()
    bytesperline = cam.bytes_per_line

    # Create a pointer to the data as a CHAR ARRAY so we can convert it to a buffer
    arr_ptr = cast(cam._p_img_mem, POINTER(c_char * (bytesperline*cam.height)))
    data = buffer(arr_ptr.contents) # buffer pointing to array of image data
    format = QImage.Format_RGB32

    image = QImage(data, cam.width, cam.height, bytesperline, format)
    return image


if __name__ == '__main__':
    cam = uc480.get_camera(serial='4002856484')
    cam.open()

    app = QApplication(sys.argv)
    ui = loader.load('snapshot_gui.ui')
    
    label = ui.findChild(QLabel, 'imageLabel')

    def load_image():
        image = get_image(cam)
        label.setPixmap(QPixmap.fromImage(image))

    button = ui.findChild(QPushButton, 'acquireButton')
    button.clicked.connect(load_image)

    ui.show()
    app.exec_()
    cam.close()
