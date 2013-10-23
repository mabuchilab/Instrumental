from ctypes import Structure, c_char
from ctypes.wintypes import WORD, DWORD, ULONG, BOOL

class SENSORINFO(Structure):
    _fields_ = [('SensorID', WORD),
                ('strSensorName', c_char*32),
                ('nColorMode', c_char),
                ('nMaxWidth', DWORD),
                ('nMaxHeight', DWORD),
                ('bMasterGain', BOOL),
                ('bRGain', BOOL),
                ('bGGain', BOOL),
                ('bBGain', BOOL),
                ('bGlobShutter', BOOL),
                ('wPixelSize', WORD),
                ('nUpperLeftBayerPixel', c_char),
                ('Reserved', c_char*13)]

class CAMERA_INFO(Structure):
    _fields_ = [('dwCameraID', DWORD),
                ('dwDeviceID', DWORD),
                ('dwSensorID', DWORD),
                ('dwInUse', DWORD),
                ('SerNo', c_char*16),
                ('Model', c_char*16),
                ('dwStatus', DWORD),
                ('dwReserved', DWORD*15)]

class CAMERA_LIST(Structure):
    _fields_ = [('dwCount', ULONG),
                ('ci', CAMERA_INFO*1)]

def create_camera_list(length):
    """ Allows us to create a CAMERA_LIST with a settable number of CAMERA_INFO items """
    try:
        length = int(length)
    except TypeError:
        length = length.value

    class CAMERA_LIST(Structure):
        _fields_ = [('dwCount', ULONG),
                    ('ci', CAMERA_INFO*length)]
    return CAMERA_LIST
