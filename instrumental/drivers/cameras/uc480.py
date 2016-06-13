# -*- coding: utf-8 -*-
# Copyright 2013-2015 Nate Bogdanowicz
"""
Driver for Thorlabs DCx cameras. May be compatible with iDS cameras that use
uEye software. Currently Windows-only, but Linux support should be
possible to implement if desired.
"""

import atexit
import logging as log
from ctypes import CDLL, WinDLL, sizeof, byref, pointer, POINTER, c_char, c_char_p, c_wchar_p, cast
from ctypes.wintypes import DWORD, INT, UINT, ULONG, DOUBLE, HWND
from ctypes.util import find_library
import numpy as np
import win32event
from . import Camera
from ._uc480.constants import *
from ._uc480.structs import *
from ..util import check_units
from .. import _ParamDict
from ...errors import InstrumentTypeError, InstrumentNotFoundError, Error, TimeoutError
from ... import Q_

import platform
if platform.architecture()[0].startswith('64'):
    lib_name = find_library('uc480_64')
    if lib_name is None:
        lib_name = find_library('ueye_api_64')
    lib = WinDLL(lib_name)
else:
    lib_name = find_library('uc480')
    if lib_name is None:
        lib = find_library('ueye_api')
    lib = CDLL(lib_name)

__all__ = ['UC480_Camera']


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

HCAM = DWORD
NULL = POINTER(HWND)()


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
                    log.info("Some cameras have duplicate IDs. Uniquifying IDs now...")
                    # Choose IDs that haven't been used yet
                    potential_ids = [i for i in range(1, len(ids)+1) if i not in ids]
                    for id in repeated:
                        new_id = potential_ids.pop(0)
                        log.info("Trying to set id from {} to {}".format(id, new_id))
                        _id = HCAM(id)
                        ret = lib.is_InitCamera(pointer(_id), NULL)
                        if not ret == IS_SUCCESS:
                            log.error("Error connecting to camera {}".format(id))
                            return None  # Avoid infinite recursion
                        else:
                            ret = lib.is_SetCameraID(_id, INT(new_id))
                            if not ret == IS_SUCCESS:
                                log.error("Error setting the camera id")
                                return None  # Avoid infinite recursion
                    # All IDs should be fixed now, let's retry
                    cams = _cameras()
            else:
                raise Error("Error getting camera list")
    else:
        raise Error("Error getting number of attached cameras")
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
        if all(cam_params[k] == v for k, v in params.items()):
            return cam_params

    raise InstrumentNotFoundError("No camera found matching the given parameters")


class BufferInfo(object):
    def __init__(self, ptr, id):
        self.ptr = ptr
        self.id = id


class UC480_Camera(Camera):
    """A uc480-supported Camera."""
    _open_cameras = []

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

        self._buffers = []
        self._queue_enabled = False
        self._trigger_mode = IS_SET_TRIGGER_OFF

        self._open()

    def __del__(self):
        if self._in_use:
            self.close()  # In case someone forgot to close()

    def set_auto_exposure(self, enable=True):
        """Enable or disable the auto exposure shutter."""
        ret = lib.is_SetAutoParameter(self._hcam, IS_SET_ENABLE_AUTO_SHUTTER,
                                      pointer(INT(enable)), NULL)
        if ret != IS_SUCCESS:
            raise Error("Failed to set auto exposure property")

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
            raise Error("Failed to open camera")

        self._in_use = True
        self._refresh_sizes()
        log.debug('image width=%d, height=%d', self.width, self.height)

        self._init_colormode()
        self._allocate_mem_seq(num_bufs)

        self._seq_event = win32event.CreateEvent(None, False, False, '')
        self._frame_event = win32event.CreateEvent(None, True, False, '')  # Don't auto-reset
        lib.is_InitEvent(self._hcam, self._seq_event.handle, IS_SET_EVENT_SEQ)
        lib.is_InitEvent(self._hcam, self._frame_event.handle, IS_SET_EVENT_FRAME)

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
        for buf in self._buffers:
            lib.is_FreeImageMem(self._hcam, buf.ptr, buf.id)
        self._buffers = []

    def _allocate_mem_seq(self, num_bufs):
        """
        Create and setup the image memory for live capture
        """
        for i in range(num_bufs):
            p_img_mem = POINTER(c_char)()
            memid = INT()
            lib.is_AllocImageMem(self._hcam, self._width, self._height, self._color_depth,
                                 pointer(p_img_mem), pointer(memid))
            lib.is_AddToSequence(self._hcam, p_img_mem, memid)
            self._buffers.append(BufferInfo(p_img_mem, memid))

        # Initialize display
        lib.is_SetImageSize(self._hcam, self._width, self._height)
        lib.is_SetDisplayMode(self._hcam, IS_SET_DM_DIB)

    def close(self):
        """Close the camera and release associated image memory.

        Should be called when you are done using the camera. Alternatively, you
        can use the camera as a context manager--see the documentation for
        __init__.
        """
        lib.is_ExitEvent(self._hcam, IS_SET_EVENT_SEQ)
        lib.is_ExitEvent(self._hcam, IS_SET_EVENT_FRAME)

        ret = lib.is_ExitCamera(self._hcam)
        if ret != IS_SUCCESS:
            log.error("Failed to close camera")
        else:
            self._in_use = False

    def _bytes_per_line(self):
        num = INT()
        ret = lib.is_GetImageMemPitch(self._hcam, pointer(num))
        if ret == IS_SUCCESS:
            log.debug('bytes_per_line=%d', num.value)
            return num.value
        raise Exception("Return code {}".format(ret))

    def _get_max_img_size(self):
        # TODO: Make this more robust
        sInfo = SENSORINFO()
        lib.is_GetSensorInfo(self._hcam, byref(sInfo))
        return int(sInfo.nMaxWidth), int(sInfo.nMaxHeight)

    def _get_sensor_color_mode(self):
        sInfo = SENSORINFO()
        lib.is_GetSensorInfo(self._hcam, byref(sInfo))
        return int(sInfo.nColorMode.encode('hex'), 16)

    def _value_getter(member_str):
        def getter(self):
            return getattr(self, member_str)
        return getter

    def _value_setter(member_str):
        def setter(self, value):
            getattr(self, member_str).value = value
        return setter

    def _array_from_buffer(self, buf):
        h = self.height
        arr = np.frombuffer(buf, np.uint8)

        if self._color_mode.value == IS_CM_RGBA8_PACKED:
            w = self.bytes_per_line/4
            arr = arr.reshape((h, w, 4), order='C')
        elif self._color_mode.value == IS_CM_BGRA8_PACKED:
            w = self.bytes_per_line/4
            arr = arr.reshape((h, w, 4), order='C')[:, :, 2::-1]
        elif self._color_mode.value == IS_CM_MONO8:
            w = self.bytes_per_line
            arr = arr.reshape((h, w), order='C')
        else:
            raise Exception("Unsupported color mode!")
        return arr

    def _set_queueing(self, enable):
        if enable:
            if not self._queue_enabled:
                lib.is_InitImageQueue(self._hcam, 0)
        else:
            if self._queue_enabled:
                lib.is_ExitImageQueue(self._hcam)
        self._queue_enabled = enable

    def _set_binning(self, vbin, hbin):
        VMAP = {
            1: IS_BINNING_DISABLE,
            2: IS_BINNING_2X_VERTICAL,
            3: IS_BINNING_3X_VERTICAL,
            4: IS_BINNING_4X_VERTICAL,
            5: IS_BINNING_5X_VERTICAL,
            6: IS_BINNING_6X_VERTICAL,
            8: IS_BINNING_8X_VERTICAL,
            16: IS_BINNING_16X_VERTICAL
        }
        HMAP = {
            1: IS_BINNING_DISABLE,
            2: IS_BINNING_2X_HORIZONTAL,
            3: IS_BINNING_3X_HORIZONTAL,
            4: IS_BINNING_4X_HORIZONTAL,
            5: IS_BINNING_5X_HORIZONTAL,
            6: IS_BINNING_6X_HORIZONTAL,
            8: IS_BINNING_8X_HORIZONTAL,
            16: IS_BINNING_16X_HORIZONTAL
        }

        mode = VMAP[vbin] | HMAP[hbin]
        ret = lib.is_SetBinning(self._hcam, mode)

        if ret == IS_NOT_SUPPORTED:
            raise Error("Unsupported binning mode (h,v) = ({},{})".format(hbin, vbin))
        elif ret != IS_SUCCESS:
            raise Error("Failed to set binning: error code {}".format(ret))

    def start_capture(self, **kwds):
        self._handle_kwds(kwds)

        self._set_binning(kwds['vbin'], kwds['hbin'])
        self._set_AOI(kwds['left'], kwds['top'], kwds['right'], kwds['bot'])
        self._set_exposure(kwds['exposure_time'])

        self._free_image_mem_seq()
        self._allocate_mem_seq(kwds['n_frames'])

        self._set_queueing(True)  # Use queue instead of ring buffer for finite sequence
        self._trigger_mode = IS_SET_TRIGGER_SOFTWARE if self._trigger_mode == IS_SET_TRIGGER_OFF else self._trigger_mode
            
        lib.is_SetExternalTrigger(self._hcam, self._trigger_mode)          
        lib.is_EnableEvent(self._hcam, IS_SET_EVENT_SEQ)
        lib.is_CaptureVideo(self._hcam, IS_DONT_WAIT)  # Trigger

    @check_units(timeout='ms')
    def get_captured_image(self, timeout='1s', copy=True):
        ret = win32event.WaitForSingleObject(self._seq_event, int(timeout.m_as('ms')))
        lib.is_DisableEvent(self._hcam, IS_SET_EVENT_SEQ)

        if ret == win32event.WAIT_TIMEOUT:
            raise TimeoutError
        elif ret != win32event.WAIT_OBJECT_0:
            raise Error("Failed to grab image")

        # Assumes we have exactly as many images as buffers
        mem_ptrs = [buf.ptr for buf in self._buffers]

        arrays = []
        for ptr in mem_ptrs:
            buf_ptr = cast(ptr, POINTER(c_char * (self.bytes_per_line*self.height)))
            array = self._array_from_buffer(buffer(buf_ptr.contents))
            arrays.append(np.copy(array) if copy else array)

        if len(arrays) == 1:
            return arrays[0]
        else:
            return tuple(arrays)

    def grab_image(self, timeout='1s', copy=True, **kwds):
        self.start_capture(**kwds)
        return self.get_captured_image(timeout=timeout, copy=copy)

    @check_units(framerate='?Hz')
    def start_live_video(self, framerate=None, **kwds):
        self._handle_kwds(kwds)

        self._set_binning(kwds['vbin'], kwds['hbin'])
        self._set_AOI(kwds['left'], kwds['top'], kwds['right'], kwds['bot'])
        self._set_exposure(kwds['exposure_time'])

        self._free_image_mem_seq()
        self._allocate_mem_seq(num_bufs=2)
        self._set_queueing(False)

        if framerate is None:
            framerate = IS_GET_FRAMERATE
        else:
            framerate = framerate.m_as('Hz')
        newFPS = DOUBLE()
        ret = lib.is_SetFrameRate(self._hcam, DOUBLE(framerate), pointer(newFPS))
        if ret != IS_SUCCESS:
            log.warn("Failed to set framerate")
        else:
            self.framerate = newFPS.value

        self._trigger_mode = IS_SET_TRIGGER_OFF
        lib.is_SetExternalTrigger(self._hcam, self._trigger_mode)
        lib.is_EnableEvent(self._hcam, IS_SET_EVENT_FRAME)
        lib.is_CaptureVideo(self._hcam, IS_WAIT)

    def stop_live_video(self):
        """Stop live video capture."""
        lib.is_StopLiveVideo(self._hcam, IS_WAIT)
        lib.is_DisableEvent(self._hcam, IS_SET_EVENT_FRAME)

    @check_units(timeout='?ms')
    def wait_for_frame(self, timeout=None):
        timeout_ms = win32event.INFINITE if timeout is None else int(timeout.m_as('ms'))
        ret = win32event.WaitForSingleObject(self._frame_event, timeout_ms)
        win32event.ResetEvent(self._frame_event)

        if ret == win32event.WAIT_TIMEOUT:
            return False
        elif ret != win32event.WAIT_OBJECT_0:
            raise Error("Failed to grab image: Windows event return code 0x{:x}".format(ret))

        return True

    def latest_frame(self, copy=True):
        nNum = INT()
        pcMem = POINTER(c_char)()
        pcMemLast = POINTER(c_char)()
        lib.is_GetActSeqBuf(self._hcam, pointer(nNum), pointer(pcMem), pointer(pcMemLast))
        buf_ptr = cast(pcMemLast, POINTER(c_char * (self.bytes_per_line*self.height)))
        array = self._array_from_buffer(buffer(buf_ptr.contents))
        return np.copy(array) if copy else array

    def _get_AOI(self):
        rect = IS_RECT()
        lib.is_AOI(self._hcam, IS_AOI_IMAGE_GET_AOI, byref(rect), sizeof(rect))
        return rect.s32X, rect.s32Y, rect.s32Width, rect.s32Height

    def _set_AOI(self, x0, y0, x1, y1):
        rect = IS_RECT(x0, y0, x1-x0, y1-y0)
        lib.is_AOI(self._hcam, IS_AOI_IMAGE_SET_AOI, byref(rect), sizeof(rect))
        self._refresh_sizes()

    def _refresh_sizes(self):
        _, _, self._width, self._height = self._get_AOI()
        self._max_width, self._max_height = self._get_max_img_size()

    @check_units(exp_time='ms')
    def _set_exposure(self, exp_time):
        param = DOUBLE(exp_time.m_as('ms'))
        cbSizeOfParam = UINT(8)
        lib.is_Exposure(self._hcam, IS_EXPOSURE_CMD_SET_EXPOSURE, byref(param), cbSizeOfParam)
        return param

    def _get_exposure(self):
        param = DOUBLE()
        lib.is_Exposure(self._hcam, IS_EXPOSURE_CMD_GET_EXPOSURE, byref(param), 8)
        return Q_(param.value, 'ms')

    def _get_exposure_inc(self):
        param = DOUBLE()
        lib.is_Exposure(self._hcam, IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_INC, byref(param), 8)
        return Q_(param.value, 'ms')

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

    def set_trigger(self, mode='software', edge='rising'):
        """Sets the camera trigger mode.

        Parameters
        ----------
        mode : string
            Either 'off', 'software'(default), or 'hardware'.
        edge : string
            Hardware trigger is either on the 'rising'(default) or 'falling' edge.	
        """
        if mode == 'off':
            new_mode = IS_SET_TRIGGER_OFF
        elif mode == 'software':
            new_mode = IS_SET_TRIGGER_SOFTWARE
        elif mode == 'hardware':
            if edge == 'rising':
                new_mode = IS_SET_TRIGGER_LO_HI
            elif edge == 'falling':
                new_mode = IS_SET_TRIGGER_HI_LO
            else: 
                raise Error("Trigger edge value {} must be either 'rising' or 'falling'".format(edge))
        else:
            raise Error("Unrecognized trigger mode {}".format(mode))

        ret = lib.is_SetExternalTrigger(self._hcam, new_mode)
        if ret != IS_SUCCESS:
            raise Error("Failed to set external trigger. Return code 0x{:x}".format(ret))
        else:    
            self._trigger_mode = new_mode

    def _get_trigger(self):
        """Get the current trigger settings
        
        Returns
        -------
        string
            off, hardware or software
        """    
        self._trigger_mode = lib.is_SetExternalTrigger(self._hcam, IS_GET_EXTERNALTRIGGER)
        
        if self._trigger_mode == IS_SET_TRIGGER_OFF:
            return 'off'
        if self._trigger_mode == IS_SET_TRIGGER_SOFTWARE:
            return 'software'
        else:
            return 'hardware'

    def get_trigger_level(self):
        """Get the current hardware trigger level
        
        Returns
        -------
        int
            A value of 0 indicates trigger signal is low (not triggered)
        """    
        return lib.is_SetExternalTrigger(self._hcam, IS_GET_TRIGGER_STATUS)
 
    @check_units(delay='?us')
    def set_trigger_delay(self, delay):
        """Sets the time to delay a hardware trigger (in microsseconds)
        
        Parameters
        ----------
        delay : string
            The delay time (in microseconds 'us') after trigger signal is received to trigger the camera
        """
        delay_us = 0 if delay is None else int(delay.m_as('us'))
        ret = lib.is_SetTriggerDelay(self._hcam, delay_us)
        if ret != IS_SUCCESS:
            raise Error("Failed to set trigger delay. Return code 0x{:x}".format(ret))
            
    def get_trigger_delay(self):
        """Returns the trigger delay in microseconds
        
        Returns
        -------
        string
            Trigger delay
        """
        param = lib.is_SetTriggerDelay(self._hcam, IS_GET_TRIGGER_DELAY)
        return Q_(param, 'us')

    #: uEye camera ID number. Read-only
    id = property(lambda self: self._id)

    #: Camera serial number string. Read-only
    serial = property(lambda self: self._serial)

    #: Camera model number string. Read-only
    model = property(lambda self: self._model)

    #: Number of bytes used by each line of the image. Read-only
    bytes_per_line = property(lambda self: self._bytes_per_line())

    #: Width of the camera image in pixels
    width = property(_value_getter('_width'))
    max_width = property(_value_getter('_max_width'))

    #: Height of the camera image in pixels
    height = property(_value_getter('_height'))
    max_height = property(_value_getter('_max_height'))

    #: Color mode string. Read-only
    color_mode = property(lambda self: self._color_mode_string())
    
    #: Trigger mode string. Read-only
    trigger_mode = property(lambda self: self._get_trigger())


@atexit.register
def _cleanup():
    for cam in UC480_Camera._open_cameras:
        try:
            cam.close()
        except:
            pass
