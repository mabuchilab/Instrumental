# -*- coding: utf-8  -*-
# Copyright 2013-2014 Nate Bogdanowicz
"""
Driver for Thorlabs DCx cameras. May be compatible with iDS cameras that use
uEye software. Currently Windows-only, but Linux support should be
possible to implement if desired.
"""

import logging as log
from ctypes import WinDLL, byref, pointer, POINTER, c_char, c_char_p, cast
from ctypes.wintypes import DWORD, INT, ULONG, DOUBLE, HWND
import os.path
import numpy as np
from . import Camera
from ._uc480_constants import *
from ._uc480_structs import *

HCAM = DWORD
NULL = POINTER(HWND)()
lib = WinDLL('uc480_64')
def errcheck(res, func, args):
    if res != IS_SUCCESS:
        raise Exception("uEye Error: {}".format(ERR_CODE_NAME[res]))
    return res
lib.is_InitCamera.errcheck = errcheck
lib.is_GetImageMemPitch.errcheck = errcheck
from .. import InstrumentTypeError, InstrumentNotFoundError, _ParamDict


def _instrument(params):
    """ Possible params include 'ueye_cam_id', 'cam_serial'"""
    print("Checking uc480...")
    d = {}
    if 'ueye_cam_id' in params:
        d['id'] = 'ueye_cam_id'
    if 'cam_serial' in params:
        d['serial'] = 'cam_serial'
    if not d:
        raise InstrumentTypeError()
    
    return UC480_Camera(**d)


def list_instruments():
    return _cameras()


def _cameras():
    """
    Get a list of ParamDicts for all cameras currently attached.
    """
    cams = []
    num = INT()
    if lib.is_GetNumberOfCameras(pointer(num)) == IS_SUCCESS:
        if num >= 1:
            cam_list = create_camera_list(num)()
            cam_list.dwCount = ULONG(num.value)  # This is stupid

            if lib.is_GetCameraList(pointer(cam_list)) == IS_SUCCESS:
                ids = []
                repeated = []
                for info in cam_list.ci:
                    id = info.dwCameraID
                    if id in ids:
                        repeated.append(id)
                    ids.append(id)

                if not repeated:
                    for info in cam_list.ci:
                        params = _ParamDict("<UC480_Camera '{}'>".format(info.SerNo))
                        params.module = 'cameras.uc480'
                        params['cam_serial'] = info.SerNo
                        params['cam_model'] = info.Model
                        params['ueye_cam_id'] = int(info.dwCameraID)
                        cams.append(params)
                else:
                    print("Some cameras have duplicate IDs. Uniquifying IDs now...")
                    # Choose IDs that haven't been used yet
                    potential_ids = [i for i in range(1, len(ids)+1) if i not in ids]
                    for id in repeated:
                        new_id = potential_ids.pop(0)
                        print("Trying to set id from {} to {}".format(id, new_id))
                        _id = HCAM(id)
                        ret = lib.is_InitCamera(pointer(_id), NULL)
                        if not ret == IS_SUCCESS:
                            print("Error connecting to camera {}".format(id))
                            return None  # Avoid infinite recursion
                        else:
                            ret = lib.is_SetCameraID(_id, INT(new_id))
                            if not ret == IS_SUCCESS:
                                print("Error setting the camera id")
                                return None  # Avoid infinite recursion
                    # All IDs should be fixed now, let's retry
                    cams = _cameras()
            else:
                print("Error getting camera list")
    else:
        print("Error getting number of attached cameras")
    return cams


def _get_legit_params(params):
    """
    Get the ParamDict of the camera that matches params. Useful for e.g.
    checking that a camera with the given id exists and for getting its serial
    and model numbers.
    """
    param_list = _cameras()
    if not param_list:
        raise InstrumentNotFoundError("No cameras attached")

    for cam_params in param_list:
        if all(cam_params[k] == v for k,v in params.items()):
            return cam_params

    raise InstrumentNotFoundError("No camera found matching the given parameters")


class UC480_Camera(Camera):
    """A uc480-supported Camera."""

    def __init__(self, id=None, serial=None):
        """Create a UC480_Camera object.

        A camera can be identified by its id, serial number, or both. If no
        arguments are given, returns the first camera it finds.

        The constructor automatically opens a connection to the camera, and the
        user is responsible for closing it. You can do this via ``close()`` or
        by using the constructor as a context manager, e.g.

            with UC480_Camera(id=1) as cam:
                cam.save_frame('image.jpg')

        Parameters
        ----------
        id : int, optional
            The uEye camera ID
        serial : str, optional
            The serial number string of the camera.
        """
        params = {}
        if id is not None:
            params['ueye_cam_id'] = id
        if serial is not None:
            params['serial'] = serial

        if params:
            params = _get_legit_params(params)
        else:
            # If given no args, just choose the 'first' camera
            param_list = _cameras()
            if not param_list:
                raise Exception("No uEye cameras attached!")
            params = param_list[0]

        self._id = int(params['ueye_cam_id'])
        self._serial = params['cam_serial']
        self._model = params['cam_model']

        self._in_use = False
        self._width, self._height = INT(), INT()
        self._color_depth = INT()
        self._color_mode = INT()
        self._p_img_mem = POINTER(c_char)()  # Never directly modify this pointer!
        self._memid = INT()
        self._list_p_img_mem = None
        self._list_memid = None

        self._open()

    def __del__(self):
        if self._in_use:
            self.close()  # In case someone forgot to close()

    def set_auto_exposure(self, enable=True):
        ret = lib.is_SetAutoParameter(self._hcam, IS_SET_ENABLE_AUTO_SHUTTER,
                                      pointer(INT(enable)), NULL)
        if ret != IS_SUCCESS:
            print("Failed to set auto exposure property")

    def load_stored_parameters(self, set_num):
        if set_num in [1, 2]:
            ret = lib.is_LoadParameters(self._hcam, c_char_p("/cam/set{}".format(set_num)))
            if ret != IS_SUCCESS:
                print("Failed to load internally stored parameters")
            else:
                # Reset original display color mode
                lib.is_GetColorDepth(self._hcam, pointer(self._color_depth),
                                     pointer(self._color_mode))
                lib.is_SetColorMode(self._hcam, self._color_mode)
        else:
            print("set_num must be either 1 or 2")

    def load_parameter_file(self, filename=None):
        if not filename:
            ptr = NULL
        else:
            ptr = c_char_p(filename)
        ret = lib.is_LoadParameters(self._hcam, ptr)
        if ret != IS_SUCCESS:
            print("Failed to load parameter file")
        else:
            # Reset original display color mode
            lib.is_GetColorDepth(self._hcam, pointer(self._color_depth), pointer(self._color_mode))
            lib.is_SetColorMode(self._hcam, self._color_mode)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _open(self, num_bufs=1):
        """
        Connect to the camera and set up the image memory.
        """
        self._hcam = HCAM(self._id)
        ret = lib.is_InitCamera(byref(self._hcam), NULL)
        print(self._hcam, self._id)
        if ret != IS_SUCCESS:
            print("Failed to open camera")
        else:
            self._in_use = True
            if num_bufs == 1:
                self._allocate_image_mem()
            else:
                self._allocate_mem_seq(num_bufs)

    def _allocate_image_mem(self):
        """
        Create and set the image memory.
        """
        self.width, self.height = self._get_max_img_size()
        log.debug('image width=%d, height=%d', self.width, self.height)

        # Set the save/display color depth to the current Windows setting
        lib.is_GetColorDepth(self._hcam, pointer(self._color_depth), pointer(self._color_mode))
        lib.is_SetColorMode(self._hcam, self._color_mode)
        log.debug('color_depth=%d, color_mode=%d', self._color_depth.value, self._color_mode.value)

        # Allocate and set memory
        lib.is_AllocImageMem(self._hcam, self._width, self._height, self._color_depth,
                             pointer(self._p_img_mem), pointer(self._memid))
        lib.is_SetImageMem(self._hcam, self._p_img_mem, self._memid)
        log.debug("Image memory allocated and set")

        # Initialize display
        lib.is_SetImageSize(self._hcam, self._width, self._height)
        lib.is_SetDisplayMode(self._hcam, IS_SET_DM_DIB)

    def _allocate_mem_seq(self, num_bufs):
        """
        Create and setup the image memory for live capture
        """
        self.width, self.height = self._get_max_img_size()

        # Set the save/display color depth to the current Windows setting
        lib.is_GetColorDepth(self._hcam, pointer(self._color_depth), pointer(self._color_mode))
        lib.is_SetColorMode(self._hcam, self._color_mode)

        self._list_p_img_mem = []
        self._list_memid = []
        for i in range(num_bufs):
            p_img_mem = POINTER(c_char)()
            memid = INT()
            lib.is_AllocImageMem(self._hcam, self._width, self._height, self._color_depth,
                                 pointer(p_img_mem), pointer(memid))
            lib.is_AddToSequence(self._hcam, p_img_mem, memid)
            self._list_p_img_mem.append(p_img_mem)
            self._list_memid.append(memid)

        # Initialize display
        lib.is_SetImageSize(self._hcam, self._width, self._height)
        lib.is_SetDisplayMode(self._hcam, IS_SET_DM_DIB)

    def _install_event_handler(self):
        import win32event
        self.hEvent = win32event.CreateEvent(None, False, False, '')
        lib.is_InitEvent(self._hcam, self.hEvent.handle, IS_SET_EVENT_FRAME)
        lib.is_EnableEvent(self._hcam, IS_SET_EVENT_FRAME)

    def _uninstall_event_handler(self):
        lib.is_DisableEvent(self._hcam, IS_SET_EVENT_FRAME)
        lib.is_ExitEvent(self._hcam, IS_SET_EVENT_FRAME)

    def close(self):
        """Close the camera and release associated image memory.

        Should be called when you are done using the camera.
        """
        ret = lib.is_ExitCamera(self._hcam)
        if ret != IS_SUCCESS:
            print("Failed to close camera")
        else:
            self._in_use = False

    def _bytes_per_line(self):
        num = INT()
        ret = lib.is_GetImageMemPitch(self._hcam, pointer(num))
        if ret == IS_SUCCESS:
            log.debug('bytes_per_line=%d', num.value)
            return num.value
        raise Exception("Return code {}".format(ret))

    def wait_for_frame(self, timeout=0):
        import win32event
        ret = win32event.WaitForSingleObject(self.hEvent, timeout)
        return (ret == win32event.WAIT_OBJECT_0)

    def freeze_frame(self):
        """Acquire an image from the camera and store it in memory.

        Can be used in conjunction with direct memory access to display an
        image without saving it to file.
        """
        ret = lib.is_FreezeVideo(self._hcam, self._width, self._height)
        log.debug("FreezeVideo retval=%d", ret)

    def start_live_video(self, framerate=None):
        self._install_event_handler()
        if framerate is None:
            framerate = IS_GET_FRAMERATE
        newFPS = DOUBLE()
        ret = lib.is_SetFrameRate(self._hcam, DOUBLE(framerate), pointer(newFPS))
        if ret != IS_SUCCESS:
            print("Error: failed to set framerate")
        else:
            self.framerate = newFPS.value

        lib.is_CaptureVideo(self._hcam, IS_WAIT)

    def stop_live_video(self):
        lib.is_StopLiveVideo(self._hcam, IS_WAIT)
        self._uninstall_event_handler()

    def save_frame(self, filename=None, filetype=None, live=False):
        """Save the current video image to disk.

        If no filename is given, this will display the 'Save as' dialog. If no
        filetype is given, it will be determined by the extension of the
        filename, if available.  If neither exists, the image will be saved as
        a bitmap (BMP) file.
        """

        # Strip extension from filename, clear extension if it is invalid
        if filename is not None:
            filename, ext = os.path.splitext(filename)
            if ext.lower() not in ['.bmp', '.jpg', '.png']:
                ext = '.bmp'
        else:
            filename, ext = '', '.bmp'

        # 'filetype' flag overrides the extension. Default is .bmp
        if filetype:
            ext = '.' + filetype.lower()

        fdict = {'.bmp': IS_IMG_BMP, '.jpg': IS_IMG_JPG, '.png': IS_IMG_PNG}
        ftype_flag = fdict[ext.lower()]
        filename = filename + ext if filename else None

        if not live:
            lib.is_FreezeVideo(self._hcam, self._width, self._height)
        lib.is_SaveImageEx(self._hcam, filename, ftype_flag, INT(0))

    def _get_max_img_size(self):
        # TODO: Make this more robust
        sInfo = SENSORINFO()
        lib.is_GetSensorInfo(self._hcam, pointer(sInfo))
        return sInfo.nMaxWidth, sInfo.nMaxHeight

    def _value_getter(member_str):
        def getter(self):
            return getattr(self, member_str).value
        return getter

    def _value_setter(member_str):
        def setter(self, value):
            getattr(self, member_str).value = value
        return setter

    def get_ndarray(self):
        # Currently only supports BGRA8_PACKED and 
        h = self.height
        arr = np.frombuffer(self.get_image_buffer(), np.uint8)
        if self._color_mode.value == IS_CM_BGRA8_PACKED:
            w = self.bytes_per_line/4
            return arr.reshape((h,w,4), order='C')[:,:,2::-1]

    def get_image_buffer(self):
        bpl = self.bytes_per_line

        # Create a pointer to the data as a CHAR ARRAY so we can convert it to a buffer
        p_img_mem = self._last_img_mem()
        arr_ptr = cast(p_img_mem, POINTER(c_char * (bpl*self.height)))
        return buffer(arr_ptr.contents)  # buffer pointing to array of image data

    def _last_img_mem(self):
        """ Returns a ctypes char-pointer to the starting address of the image memory
        last used for image capturing """
        if self._list_p_img_mem is None:
            # Just using a single image buffer
            return self._p_img_mem
        else:
            # Using a buffer sequence
            nNum = INT()
            pcMem = POINTER(c_char)()
            pcMemLast = POINTER(c_char)()
            lib.is_GetActSeqBuf(self._hcam, pointer(nNum), pointer(pcMem), pointer(pcMemLast))
            return pcMemLast

    #: uEye camera ID number. Read-only
    id = property(lambda self: self._id)

    #: Camera serial number string. Read-only
    serial = property(lambda self: self._serial)

    #: Camera model number string. Read-only
    model = property(lambda self: self._model)

    #: Number of bytes used by each line of the image. Read-only
    bytes_per_line = property(lambda self: self._bytes_per_line())

    #: Width of the camera image in pixels
    width = property(_value_getter('_width'), _value_setter('_width'))

    #: Height of the camera image in pixels
    height = property(_value_getter('_height'), _value_setter('_height'))


if __name__ == '__main__':
    cam = _get_camera(serial='4002856484')
    cam.save_frame('cool.jpg')
    cam.close()
