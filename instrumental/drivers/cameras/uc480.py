# -*- coding: utf-8 -*-
# Copyright 2013-2015 Nate Bogdanowicz
"""
Driver for Thorlabs DCx cameras. May be compatible with iDS cameras that use
uEye software. Currently Windows-only, but Linux support should be
possible to implement if desired.
"""

import logging as log
from ctypes import CDLL, WinDLL, byref, pointer, POINTER, c_char, c_char_p, c_wchar_p, cast
from ctypes.wintypes import DWORD, INT, ULONG, DOUBLE, HWND
import os.path
import numpy as np
from . import Camera
from ._uc480.constants import *
from ._uc480.structs import *

HCAM = DWORD
NULL = POINTER(HWND)()

import platform
if platform.architecture()[0].startswith('64'):
    lib = WinDLL('ueye_api_64') ###WinDLL('uc480_64')
else:
    lib = CDLL('uc480')

def errcheck(res, func, args):
    if res != IS_SUCCESS:
        if func == lib.is_SetColorMode and args[1] == IS_GET_COLOR_MODE:
            pass
        else:
            raise Exception("uEye Error: {}".format(ERR_CODE_NAME[res]))
    return res
lib.is_InitCamera.errcheck = errcheck
lib.is_GetImageMemPitch.errcheck = errcheck
lib.is_SetColorMode.errcheck = errcheck
from .. import _ParamDict
from ...errors import InstrumentTypeError, InstrumentNotFoundError


def _instrument(params):
    """ Possible params include 'ueye_cam_id', 'cam_serial'"""
    d = {}
    if 'ueye_cam_id' in params:
        d['id'] = params['ueye_cam_id']
    if 'cam_serial' in params:
        d['serial'] = params['cam_serial']
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
    if lib.is_GetNumberOfCameras(byref(num)) == IS_SUCCESS:
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

            >>> with UC480_Camera(id=1) as cam:
            >>>     cam.save_image('image.jpg')

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
            params['cam_serial'] = serial

        if params:
            params = _get_legit_params(params)
        else:
            # If given no args, just choose the 'first' camera
            param_list = _cameras()
            if not param_list:
                raise Exception("No uEye cameras attached!")
            params = param_list[0]

        # For saving
        self._param_dict = params
        self._param_dict.module = 'cameras.uc480'
        self._param_dict['module'] = 'cameras.uc480'

        self._id = int(params['ueye_cam_id'])
        self._serial = params['cam_serial']
        self._model = params['cam_model']

        self._in_use = False
        self._width, self._height = INT(), INT()
        self._color_depth = INT()
        self._color_mode = INT()
        self._list_p_img_mem = None
        self._list_memid = None
        self.is_live = False

        self._open()

    def __del__(self):
        if self._in_use:
            self.close()  # In case someone forgot to close()

    def set_auto_exposure(self, enable=True):
        """Enable or disable the auto exposure shutter."""
        ret = lib.is_SetAutoParameter(self._hcam, IS_SET_ENABLE_AUTO_SHUTTER,
                                      pointer(INT(enable)), NULL)
        if ret != IS_SUCCESS:
            print("Failed to set auto exposure property")

    def load_params(self, filename=None):
        """Load camera parameters from file or EEPROM.

        Parameters
        ----------
        filename : str, optional
            By default, loads the parameters from the camera's EEPROM. Otherwise,
            loads it from the specified parameter file. If filename is the empty
            string '', will open a 'Load' dialog to select the file.
        """
        if filename is None:
            cmd = IS_PARAMETERSET_CMD_LOAD_EEPROM
            param = c_char_p("/cam/set1")
            size = len(param.value)
        else:
            cmd = IS_PARAMETERSET_CMD_LOAD_FILE
            param = c_wchar_p(filename)
            size = len(param.value)

        ret = lib.is_ParameterSet(self._hcam, cmd, param, size)
        if ret == IS_INVALID_CAMERA_TYPE:
            raise Exception(".ini file does not match the camera model")
        elif ret != IS_SUCCESS:
            if filename != '':
                raise Exception("Failed to load parameter file")
        else:
            # Make sure memory is set up for right color depth
            depth_map = {
                IS_CM_MONO8: 8,
                IS_CM_RGBA8_PACKED: 32,
                IS_CM_BGRA8_PACKED: 32
            }
            mode = lib.is_SetColorMode(self._hcam, IS_GET_COLOR_MODE)
            depth = depth_map[mode]
            if depth != self._color_depth.value:
                log.debug("Color depth changed from %s to %s",
                    self._color_depth.value, depth)
                self._free_image_mem_seq()
                self._color_depth = INT(depth)
                self._allocate_image_mem_seq()
            self._color_mode = INT(mode)

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
        if ret != IS_SUCCESS:
            print("Failed to open camera")
        else:
            self._in_use = True
            self.width, self.height = self._get_max_img_size()
            log.debug('image width=%d, height=%d', self.width, self.height)

            self._init_colormode()
            self._allocate_mem_seq(num_bufs)

    def _init_colormode(self):
        log.debug("Initializing default color mode")
        sensor_mode = self._get_sensor_color_mode()
        mode_map = {
            IS_COLORMODE_MONOCHROME: (IS_CM_MONO8, 8),
            IS_COLORMODE_BAYER: (IS_CM_RGBA8_PACKED, 32)
        }
        try:
            mode, depth = mode_map[sensor_mode]
        except KeyError:
            raise Exception("Currently unsupported sensor color mode!")

        self._color_mode, self._color_depth = DWORD(mode), DWORD(depth)
        log.debug('color_depth=%d, color_mode=%d', depth, mode)

        lib.is_SetColorMode(self._hcam, self._color_mode)

    def _free_image_mem_seq(self):
        lib.is_ClearSequence(self._hcam)
        for p_img_mem, memid in zip(self._list_p_img_mem, self._list_memid):
            lib.is_FreeImageMem(self._hcam, p_img_Mem, memid)
        self._list_p_img_mem = None
        self._list_memid = None

    def _allocate_mem_seq(self, num_bufs):
        """
        Create and setup the image memory for live capture
        """
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
        try:
            import win32event
        except ImportError:
            raise ImportError("Live video events require the win32event module")
        self.hEvent = win32event.CreateEvent(None, False, False, '')
        lib.is_InitEvent(self._hcam, self.hEvent.handle, IS_SET_EVENT_FRAME)
        lib.is_EnableEvent(self._hcam, IS_SET_EVENT_FRAME)

    def _uninstall_event_handler(self):
        lib.is_DisableEvent(self._hcam, IS_SET_EVENT_FRAME)
        lib.is_ExitEvent(self._hcam, IS_SET_EVENT_FRAME)

    def close(self):
        """Close the camera and release associated image memory.

        Should be called when you are done using the camera. Alternatively, you
        can use the camera as a context manager--see the documentation for
        __init__.
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
        """ Wait for FRAME event to be signaled. 
            
            Parameters
            ----------
            timeout : int, optional
                How long to wait for event to be signaled. If timeout is 0,
                this polls the event status and reterns immediately.

            Returns
            -------
            bool
                Whether FRAME event was signaled.
        """
        try:
            import win32event
        except ImportError:
            raise ImportError("Live video events require the win32event module")
        ret = win32event.WaitForSingleObject(self.hEvent, timeout)
        return (ret == win32event.WAIT_OBJECT_0)

    def freeze_frame(self, wait_trigger=IS_WAIT):
        """Acquire an image from the camera and store it in memory. wait_trigger in increments of 10ms.

        Can be used in conjunction with direct memory access to display an
        image without saving it to file.
        """
        ret = lib.is_FreezeVideo(self._hcam, wait_trigger)
        log.debug("FreezeVideo retval=%d", ret)

    def start_live_video(self, framerate=None):
        """Start live video capture.
        
        Parameters
        ----------
        framerate : float, optional
            Desired framerate. The true framerate that results can be found in
            the ``framerate`` attribute.
        """
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
        self.is_live = True
        
    def stop_live_video(self):
        """Stop live video capture."""
        lib.is_StopLiveVideo(self._hcam, IS_WAIT)
        self._uninstall_event_handler()
        self.is_live = False
        
    def set_trigger_delay(self,us):
        '''set trigger delay in microseconds (us).'''
        ret = lib.is_SetTriggerDelay(self._hcam, us)
        if ret != IS_SUCCESS:
            print("Error: failed to set trigger delay")
            
    def set_hardware_trigger(self, mode=IS_SET_TRIGGER_LO_HI):
        '''use hardware trigger. Default to rising edge'''
        ret = lib.is_SetExternalTrigger(self._hcam, mode)
        if ret != IS_SUCCESS:
            print("Error: failed to set external trigger")

        
    def save_image(self, filename=None, filetype=None, freeze=None):
        """Save the current video image to disk.

        If no filename is given, this will display the 'Save as' dialog. If no
        filetype is given, it will be determined by the extension of the
        filename, if available.  If neither exists, the image will be saved as
        a bitmap (BMP) file.

        Parameters
        ----------
        filename : str, optional
            Filename to save image as. If not given, 'Save as' dialog will open.
        filetype : str, optional
            Filetype to save image as, e.g. 'bmp'. Useful for setting the
            default filetype in the 'Save as' dialog.
        freeze : bool, optional
            Freeze a frame before copying data. By default, freezes when not in
            live capture mode.
        """
        if freeze is None:
            freeze = not self.is_live

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

        if freeze:
            lib.is_FreezeVideo(self._hcam, self._width, self._height)
        lib.is_SaveImageEx(self._hcam, filename, ftype_flag, INT(0))

    def _get_max_img_size(self):
        # TODO: Make this more robust
        sInfo = SENSORINFO()
        lib.is_GetSensorInfo(self._hcam, byref(sInfo))
        return sInfo.nMaxWidth, sInfo.nMaxHeight

    def _get_sensor_color_mode(self):
        sInfo = SENSORINFO()
        lib.is_GetSensorInfo(self._hcam, byref(sInfo))
        return int(sInfo.nColorMode.encode('hex'), 16)

    def _value_getter(member_str):
        def getter(self):
            return getattr(self, member_str).value
        return getter

    def _value_setter(member_str):
        def setter(self, value):
            getattr(self, member_str).value = value
        return setter

    def image_array(self, freeze=True):
        """ Get an array of the data in the active image memory.

        The array's shape depends on the camera's color mode. Monochrome modes
        return an array with shape (height, width), while camera modes return
        an array with shape (height, width, 3) where the last axis contains the
        RGB channels in that order.

        This format is useful for sending to matplotlib's ``imshow()``
        function::

            >>> ...
            >>> import matplotlib.pyplot as plt
            >>> cam.freeze_frame()
            >>> plt.imshow(cam.image_array())
            >>> plt.show()

        Parameters
        ----------
        freeze : bool, optional
            Freeze a frame before copying data. By default, freezes when not in
            live capture mode.
        """
        # Currently only supports MONO8 and RGBA8_PACKED
        if (not self.is_live if freeze is None else freeze):
            lib.is_FreezeVideo(self._hcam, self._width, self._height)

        h = self.height
        arr = np.frombuffer(self.image_buffer(), np.uint8)

        if self._color_mode.value == IS_CM_RGBA8_PACKED:
            w = self.bytes_per_line/4
            arr = arr.reshape((h,w,4), order='C')
        elif self._color_mode.value == IS_CM_BGRA8_PACKED:
            w = self.bytes_per_line/4
            arr = arr.reshape((h,w,4), order='C')[:,:,2::-1]
        elif self._color_mode.value == IS_CM_MONO8:
            w = self.bytes_per_line
            arr = arr.reshape((h,w), order='C')
        else:
            raise Exception("Unsupported color mode!")
        return arr

    def image_buffer(self):
        """ Get a buffer of the active image memory's bytes. """
        bpl = self.bytes_per_line

        # Create a pointer to the data as a CHAR ARRAY so we can convert it to a buffer
        p_img_mem = self._last_img_mem()
        arr_ptr = cast(p_img_mem, POINTER(c_char * (bpl*self.height)))
        return buffer(arr_ptr.contents)  # buffer pointing to array of image data

    def _last_img_mem(self):
        """ Returns a ctypes char-pointer to the starting address of the image memory
        last used for image capturing """
        nNum = INT()
        pcMem = POINTER(c_char)()
        pcMemLast = POINTER(c_char)()
        lib.is_GetActSeqBuf(self._hcam, pointer(nNum), pointer(pcMem), pointer(pcMemLast))
        return pcMemLast

    def _color_mode_string(self):
        MAP = {
            IS_CM_MONO8: 'mono8',
            IS_CM_MONO16: 'mono16',
        }
        return MAP.get(self._color_mode.value)

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

    #: Color mode string. Read-only
    color_mode = property(lambda self: self._color_mode_string())


if __name__ == '__main__':
    with UC480_Camera(serial='4002856484') as cam:
        cam.save_image('cool.jpg')
