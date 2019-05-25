# -*- coding: utf-8 -*-
# Copyright 2013-2018 Nate Bogdanowicz
"""
Driver for Thorlabs DCx cameras. May be compatible with iDS cameras that use
uEye software. Currently Windows-only, but Linux support should be
possible to implement if desired.
"""
from past.builtins import basestring, unicode

import struct
import weakref
import fnmatch
import numpy as np
import win32event  # req: pywin32

from nicelib import (NiceLib, NiceObject, load_lib,
                     RetHandler, Sig, ret_return)  # req: nicelib >= 0.5

from . import Camera
from ..util import check_units
from .. import ParamSet, Facet
from ...errors import (InstrumentNotFoundError, Error, TimeoutError, LibError,
                       UnsupportedFeatureError)
from ...log import get_logger
from ... import Q_

log = get_logger(__name__)

_INST_PARAMS = ['serial', 'id', 'model']
_INST_CLASSES = ['UC480_Camera']

info = load_lib('uc480', __package__)
ffi = info._ffi

__all__ = ['UC480_Camera']

global_weakkeydict = weakref.WeakKeyDictionary()


def to_bytes(text):
    if isinstance(text, bytes):
        return text
    elif isinstance(text, unicode):
        text.encode('utf-8')


def char_to_int(char):
    return struct.unpack('B', char)[0]


def cmd_ret_handler(getcmd_names, cmd_pos=1):
    """Create an error wrapping function for a UC480 command-taking function.

    A bunch of UC480 functions take ints indicating a "command" to run. Often, "get" commands will
    use the return value to return their value, while "set" commands will use it as an error code.
    This function helps generate a wrapper that will disable error-checking if one of the given
    "get" commands is passed in.

    getcmd_names : sequence of strs
        glob patterns which match the names of the GET command constants for this function
    cmd_pos : int
        the position of the command UINT in the function's arglist
    """
    if isinstance(getcmd_names, basestring):
        getcmd_names = (getcmd_names,)

    getcmd_vals = [info._defs[const_name]
                   for pattern in getcmd_names
                   for const_name in fnmatch.filter(info._defs.keys(), pattern)]

    # Note: we don't specify num_retvals, since it depends on the command issued
    @RetHandler
    def wrap(result, funcargs, niceobj):
        # Need to cast in case arg is CData
        if int(funcargs[cmd_pos]) in getcmd_vals:
            return result
        elif result != info._defs['IS_SUCCESS']:
            err_code, err_msg = niceobj.GetError()
            raise UC480Error(code=result, msg=err_msg)

    return wrap


class UC480Error(LibError):
    MESSAGES = {
        -1: "Undefined error occurred",
        1: "Invalid camera handle",
        2: ("An IO request from the uc480 driver failed. Maybe the versions of the DLL (API) and "
            "the driver (.sys) file do not match"),
        3: ("An attempt to initialize or select the camera failed (no camera connected or "
            "initialization error)"),
    }


def sig(*args):
    def decorator(func):
        func.sig = args
        return func
    return decorator


@RetHandler(num_retvals=0)
def ret_errcheck(result):
    if result != NiceUC480.SUCCESS:
        raise UC480Error(code=result)


@RetHandler(num_retvals=0)
def ret_cam_errcheck(result, niceobj):
    if result != NiceUC480.SUCCESS:
        err_code, err_msg = niceobj.GetError()
        raise UC480Error(code=result, msg=err_msg)


class NiceUC480(NiceLib):
    _info_ = info
    _prefix_ = ('is_', 'IS_')
    _ret_ = ret_errcheck

    # Classmethods
    #
    GetNumberOfCameras = Sig('out')
    GetCameraList = Sig('inout')
    InitCamera = Sig('inout', 'in')

    # Camera methods
    #
    class Camera(NiceObject):
        _init_ = 'InitCamera'
        _ret_ = ret_cam_errcheck

        AddToSequence = Sig('in', 'in', 'in')
        AllocImageMem = Sig('in', 'in', 'in', 'in', 'out', 'out')
        CaptureVideo = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_LIVE'))
        ClearSequence = Sig('in')
        DisableEvent = Sig('in', 'in')
        EnableEvent = Sig('in', 'in')
        ExitCamera = Sig('in')
        ExitEvent = Sig('in', 'in')
        ExitImageQueue = Sig('in')
        FreeImageMem = Sig('in', 'in', 'in')
        GetActSeqBuf = Sig('in', 'out', 'out', 'out')
        GetError = Sig('in', 'out', 'bufout')
        GetImageMemPitch = Sig('in', 'out')
        GetSensorInfo = Sig('in', 'out')
        HasVideoStarted = Sig('in', 'out')
        InitEvent = Sig('in', 'in', 'in')
        InitImageQueue = Sig('in', 'in')
        ParameterSet = Sig('in', 'in', 'inout', 'in')
        ResetToDefault = Sig('in')
        SetAutoParameter = Sig('in', 'in', 'inout', 'inout')
        SetBinning = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_*BINNING*'))
        SetCameraID = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_CAMERA_ID'))
        SetColorMode = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_COLOR_MODE'))
        SetDisplayMode = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_DISPLAY_MODE'))
        SetExternalTrigger = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_*TRIGGER*'))
        SetFrameRate = Sig('in', 'in', 'out')
        SetGainBoost = Sig('in', 'in', ret=cmd_ret_handler(('IS_GET_GAINBOOST',
                                                           'IS_GET_SUPPORTED_GAINBOOST')))
        SetHWGainFactor = Sig('in', 'in', 'in', ret=ret_return)
        SetSubSampling = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_*SUBSAMPLING*'))
        SetTriggerDelay = Sig('in', 'in', ret=cmd_ret_handler('IS_GET_*TRIGGER*'))
        StopLiveVideo = Sig('in', 'in')
        SetHardwareGain = Sig('in', 'in', 'in', 'in', 'in',
                              ret=cmd_ret_handler(
                                  ('IS_GET_MASTER_GAIN', 'IS_GET_RED_GAIN', 'IS_GET_GREEN_GAIN',
                                   'IS_GET_BLUE_GAIN', 'IS_GET_DEFAULT_MASTER',
                                   'IS_GET_DEFAULT_RED', 'IS_GET_DEFAULT_GREEN',
                                   'IS_GET_DEFAULT_BLUE')))

        # Hand-wrapped methods
        #
        @Sig('in', 'in', 'inout', 'in')
        def AOI(self, command, param=None):
            """AOI(command, param=None)"""
            if command & lib.AOI_MULTI_GET_AOI:
                if command == lib.AOI_MULTI_GET_AOI:
                    raise Error("command AOI_MULTI_GET_AOI must be or'd together with another flag")
                param_type = 'UINT[8]'
                getting = True
            elif command in AOI_GET_PARAM_TYPES:
                param_type = AOI_GET_PARAM_TYPES[command]
                getting = True
            elif command in AOI_SET_PARAM_TYPES:
                param_type = AOI_SET_PARAM_TYPES[command]
                getting = False
            else:
                raise Error("Unsupported command given")

            if getting and param is not None:
                raise ValueError("Cannot give a param value when using a GET command")
            elif not getting and param is None:
                raise ValueError("Must give a param value when using a SET command")

            param_type = ffi.typeof(param_type)
            deref = (param_type.kind == 'pointer')  # Don't dereference arrays

            param_data = ffi.new(param_type, param)
            size = ffi.sizeof(ffi.typeof(param_data).item if deref else param_data)
            param_ptr = ffi.cast('void*', param_data)
            self._autofunc_AOI(command, param_ptr, size)

            if getting:
                return param_data[0] if deref else param_data

        @Sig('in', 'in', 'inout', 'in')
        def Exposure(self, command, param=None):
            if command in EXPOSURE_GET_PARAM_TYPES:
                param_type = EXPOSURE_GET_PARAM_TYPES[command]
                getting = True
            elif command in EXPOSURE_SET_PARAM_TYPES:
                param_type = EXPOSURE_SET_PARAM_TYPES[command]
                getting = False
            else:
                raise Error("Unsupported command given")

            if getting and param is not None:
                raise ValueError("Cannot give a param value when using a GET command")
            elif not getting and param is None:
                raise ValueError("Must give a param value when using a SET command")

            param_type = ffi.typeof(param_type)
            deref = (param_type.kind == 'pointer')  # Don't dereference arrays

            param_data = ffi.new(param_type, param)
            size = ffi.sizeof(ffi.typeof(param_data).item if deref else param_data)
            param_ptr = ffi.cast('void*', param_data)
            self._autofunc_Exposure(command, param_ptr, size)

            if getting:
                return param_data[0] if deref else param_data

        @Sig('in', 'in', 'inout', 'in')
        def Gamma(self, command, param=None):
            if command in (lib.GAMMA_CMD_GET, lib.GAMMA_CMD_GET_DEFAULT):
                getting = True
            elif command == lib.GAMMA_CMD_SET:
                getting = False
            else:
                raise ValueError("Unsupported command given")

            if getting and param is not None:
                raise ValueError("Cannot give a param value when using a GET command")
            elif not getting and param is None:
                raise ValueError("Must give a param value when using a SET command")

            param_data = ffi.new('INT*', param)
            size = ffi.sizeof('INT')
            param_ptr = ffi.cast('void*', param_data)
            self._autofunc_Gamma(command, param_ptr, size)

            if getting:
                return param_data[0]

        @Sig('in', 'in', 'inout', 'in')
        def Blacklevel(self, command, param=None):
            if command in BLACKLEVEL_GET_PARAM_TYPES:
                param_type = BLACKLEVEL_GET_PARAM_TYPES[command]
                getting = True
            elif command in BLACKLEVEL_SET_PARAM_TYPES:
                param_type = BLACKLEVEL_SET_PARAM_TYPES[command]
                getting = False
            else:
                raise Error("Unsupported command given")

            if getting and param is not None:
                raise ValueError("Cannot give a param value when using a GET command")
            elif not getting and param is None:
                raise ValueError("Must give a param value when using a SET command")

            param_type = ffi.typeof(param_type)
            deref = (param_type.kind == 'pointer')  # Don't dereference arrays

            param_data = ffi.new(param_type, param)
            size = ffi.sizeof(ffi.typeof(param_data).item if deref else param_data)
            param_ptr = ffi.cast('void*', param_data)
            self._autofunc_Blacklevel(command, param_ptr, size)

            if getting:
                return param_data[0] if deref else param_data

        @Sig('in', 'in', 'inout', 'in')
        def PixelClock(self, command, param=None):
            if command in PIXELCLOCK_GET_PARAM_TYPES:
                param_type = PIXELCLOCK_GET_PARAM_TYPES[command]
                getting = True
            elif command in PIXELCLOCK_SET_PARAM_TYPES:
                param_type = PIXELCLOCK_SET_PARAM_TYPES[command]
                getting = False
            else:
                raise Error("Unsupported command given")

            if getting and param is not None:
                raise ValueError("Cannot give a param value when using a GET command")
            elif not getting and param is None:
                raise ValueError("Must give a param value when using a SET command")

            param_type = ffi.typeof(param_type)
            deref = (param_type.kind == 'pointer')  # Don't dereference arrays

            param_data = ffi.new(param_type, param)
            size = ffi.sizeof(ffi.typeof(param_data).item if deref else param_data)
            param_ptr = ffi.cast('void*', param_data)
            self._autofunc_PixelClock(command, param_ptr, size)

            if getting:
                return param_data[0] if deref else param_data


lib = NiceUC480

# Shim to support older versions of uc480.h
if not hasattr(lib, 'AOI_IMAGE_GET_POS_FAST_SUPPORTED'):
    lib.AOI_IMAGE_GET_POS_FAST_SUPPORTED = lib.AOI_IMAGE_SET_POS_FAST_SUPPORTED

AOI_GET_PARAM_TYPES = {
    lib.AOI_IMAGE_GET_AOI: 'IS_RECT*',
    lib.AOI_IMAGE_GET_POS: 'IS_POINT_2D*',
    lib.AOI_IMAGE_GET_SIZE: 'IS_SIZE_2D*',
    lib.AOI_IMAGE_GET_POS_MIN: 'IS_POINT_2D*',
    lib.AOI_IMAGE_GET_SIZE_MIN: 'IS_SIZE_2D*',
    lib.AOI_IMAGE_GET_POS_MAX: 'IS_POINT_2D*',
    lib.AOI_IMAGE_GET_SIZE_MAX: 'IS_SIZE_2D*',
    lib.AOI_IMAGE_GET_POS_INC: 'IS_POINT_2D*',
    lib.AOI_IMAGE_GET_SIZE_INC: 'IS_SIZE_2D*',
    lib.AOI_IMAGE_GET_POS_X_ABS: 'UINT*',
    lib.AOI_IMAGE_GET_POS_Y_ABS: 'UINT*',
    lib.AOI_IMAGE_GET_ORIGINAL_AOI: 'IS_RECT*',
    lib.AOI_AUTO_BRIGHTNESS_GET_AOI: 'IS_RECT*',
    lib.AOI_AUTO_WHITEBALANCE_GET_AOI: 'IS_RECT*',
    lib.AOI_MULTI_GET_SUPPORTED_MODES: 'UINT*',
    lib.AOI_SEQUENCE_GET_SUPPORTED: 'UINT*',
    lib.AOI_SEQUENCE_GET_PARAMS: 'AOI_SEQUENCE_PARAMS*',
    lib.AOI_SEQUENCE_GET_ENABLE: 'UINT*',
    lib.AOI_IMAGE_GET_POS_FAST_SUPPORTED: 'UINT*',
}

AOI_SET_PARAM_TYPES = {
    lib.AOI_IMAGE_SET_AOI: 'IS_RECT*',
    lib.AOI_IMAGE_SET_POS: 'IS_POINT_2D*',
    lib.AOI_IMAGE_SET_SIZE: 'IS_SIZE_2D*',
    lib.AOI_IMAGE_SET_POS_FAST: 'IS_POINT_2D*',
    lib.AOI_AUTO_BRIGHTNESS_SET_AOI: 'IS_RECT*',
    lib.AOI_AUTO_WHITEBALANCE_SET_AOI: 'IS_RECT*',

    # TODO: Implement these commands
    lib.AOI_MULTI_SET_AOI: '',
    lib.AOI_MULTI_DISABLE_AOI: '',
    lib.AOI_SEQUENCE_SET_PARAMS: '',
    lib.AOI_SEQUENCE_SET_ENABLE: '',
}

BLACKLEVEL_GET_PARAM_TYPES = {
    lib.BLACKLEVEL_CMD_GET_CAPS: 'INT*',
    lib.BLACKLEVEL_CMD_GET_MODE_DEFAULT: 'INT*',
    lib.BLACKLEVEL_CMD_GET_MODE: 'INT*',
    lib.BLACKLEVEL_CMD_GET_OFFSET_DEFAULT: 'INT*',
    lib.BLACKLEVEL_CMD_GET_OFFSET_RANGE: 'IS_RANGE_S32*',
    lib.BLACKLEVEL_CMD_GET_OFFSET: 'INT*',
}

BLACKLEVEL_SET_PARAM_TYPES = {
    lib.BLACKLEVEL_CMD_SET_MODE: 'INT*',
    lib.BLACKLEVEL_CMD_SET_OFFSET: 'INT*',
}

PIXELCLOCK_GET_PARAM_TYPES = {
    lib.PIXELCLOCK_CMD_GET_NUMBER: 'UINT*',
    lib.PIXELCLOCK_CMD_GET_LIST: 'UINT[150]',
    lib.PIXELCLOCK_CMD_GET_RANGE: 'UINT[3]',
    lib.PIXELCLOCK_CMD_GET_DEFAULT: 'UINT*',
    lib.PIXELCLOCK_CMD_GET: 'UINT*',
}

PIXELCLOCK_SET_PARAM_TYPES = {
    lib.PIXELCLOCK_CMD_SET: 'UINT*',
}

EXPOSURE_GET_PARAM_TYPES = {
    lib.IS_EXPOSURE_CMD_GET_CAPS: 'UINT*',
    lib.IS_EXPOSURE_CMD_GET_EXPOSURE_DEFAULT: 'double*',
    lib.IS_EXPOSURE_CMD_GET_EXPOSURE: 'double*',
    lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MIN: 'double*',
    lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MAX: 'double*',
    lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_INC: 'double*',
    lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE: 'double[3]',
    lib.IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_MIN: 'double*',
    lib.IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_MAX: 'double*',
    lib.IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_INC: 'double*',
    lib.IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE: 'double[3]',
    lib.IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_MIN: 'double*',
    lib.IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_MAX: 'double*',
    lib.IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_INC: 'double*',
    lib.IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE: 'double[3]',
    lib.IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_ENABLE: 'UINT*',
}

EXPOSURE_SET_PARAM_TYPES = {
    lib.IS_EXPOSURE_CMD_SET_EXPOSURE: 'double*',
    lib.IS_EXPOSURE_CMD_SET_LONG_EXPOSURE_ENABLE: 'UINT*',
}

SUBSAMP_V_CODE_FROM_NUM = {
    1: lib.SUBSAMPLING_DISABLE,
    2: lib.SUBSAMPLING_2X_VERTICAL,
    3: lib.SUBSAMPLING_3X_VERTICAL,
    4: lib.SUBSAMPLING_4X_VERTICAL,
    5: lib.SUBSAMPLING_5X_VERTICAL,
    6: lib.SUBSAMPLING_6X_VERTICAL,
    8: lib.SUBSAMPLING_8X_VERTICAL,
    16: lib.SUBSAMPLING_16X_VERTICAL,
}
SUBSAMP_H_CODE_FROM_NUM = {
    1: lib.SUBSAMPLING_DISABLE,
    2: lib.SUBSAMPLING_2X_HORIZONTAL,
    3: lib.SUBSAMPLING_3X_HORIZONTAL,
    4: lib.SUBSAMPLING_4X_HORIZONTAL,
    5: lib.SUBSAMPLING_5X_HORIZONTAL,
    6: lib.SUBSAMPLING_6X_HORIZONTAL,
    8: lib.SUBSAMPLING_8X_HORIZONTAL,
    16: lib.SUBSAMPLING_16X_HORIZONTAL,
}

BIN_V_CODE_FROM_NUM = {
    1: lib.BINNING_DISABLE,
    2: lib.BINNING_2X_VERTICAL,
    3: lib.BINNING_3X_VERTICAL,
    4: lib.BINNING_4X_VERTICAL,
    5: lib.BINNING_5X_VERTICAL,
    6: lib.BINNING_6X_VERTICAL,
    8: lib.BINNING_8X_VERTICAL,
    16: lib.BINNING_16X_VERTICAL
}
BIN_H_CODE_FROM_NUM = {
    1: lib.BINNING_DISABLE,
    2: lib.BINNING_2X_HORIZONTAL,
    3: lib.BINNING_3X_HORIZONTAL,
    4: lib.BINNING_4X_HORIZONTAL,
    5: lib.BINNING_5X_HORIZONTAL,
    6: lib.BINNING_6X_HORIZONTAL,
    8: lib.BINNING_8X_HORIZONTAL,
    16: lib.BINNING_16X_HORIZONTAL
}


def list_instruments():
    return _cameras()


def camera_info_list():
    """
    Note that the returned array object must be kept alive, or the struct memory will become
    garbage.
    """
    num_cams = lib.GetNumberOfCameras()
    if not num_cams:
        return []

    n_bytes = ffi.sizeof('DWORD') + num_cams * ffi.sizeof('UC480_CAMERA_INFO')
    mem = ffi.new('BYTE[]', n_bytes)
    cam_list_struct = ffi.cast('UC480_CAMERA_LIST*', mem)
    cam_list_struct.dwCount = num_cams

    lib.GetCameraList(cam_list_struct)

    info_list = ffi.cast('UC480_CAMERA_INFO[%d]' % num_cams, cam_list_struct.uci)
    global_weakkeydict[info_list] = mem  # Keep mem from being cleaned up
    return info_list


def _cameras():
    """Get a list of ParamSets for all cameras currently attached."""
    cam_list = camera_info_list()
    if not cam_list:
        return []

    cams = []
    ids = []
    repeated = []
    for info in cam_list:
        id = info.dwCameraID
        if id in ids:
            repeated.append(id)
        ids.append(id)

    if not repeated:
        for info in cam_list:
            params = ParamSet(UC480_Camera,
                              serial=ffi.string(info.SerNo),
                              model=ffi.string(info.Model),
                              id=int(info.dwCameraID))
            cams.append(params)

    else:
        log.info("Some cameras have duplicate IDs. Uniquifying IDs now...")
        # Choose IDs that haven't been used yet
        potential_ids = [i for i in range(1, len(ids)+1) if i not in ids]
        for id in repeated:
            new_id = potential_ids.pop(0)
            log.info("Trying to set id from {} to {}".format(id, new_id))

            try:
                dev = lib.Camera(id, ffi.NULL)
            except Error:
                log.error("Error connecting to camera {}".format(id))
                return []  # Avoid infinite recursion

            try:
                dev.SetCameraID(new_id)
            except Error:
                log.error("Error setting the camera id")
                return []  # Avoid infinite recursion

        # All IDs should be fixed now, let's retry
        cams = _cameras()

    return cams


def _get_legit_params(params):
    """
    Get the ParamSet of the camera that matches params. Useful for e.g.
    checking that a camera with the given id exists and for getting its serial
    and model numbers.
    """
    param_list = _cameras()
    if not param_list:
        raise InstrumentNotFoundError("No cameras attached")

    for cam_params in param_list:
        if all(cam_params[k] == v for k, v in params.items() if v is not None):
            return cam_params

    raise InstrumentNotFoundError("No camera found matching the given parameters")


def AutoParamEnableFacet(name, doc=None):
    GET_CMD = getattr(lib, 'GET_ENABLE_' + name)
    SET_CMD = getattr(lib, 'SET_ENABLE_' + name)
    def fget(self):
        val1, val2 = self._dev.SetAutoParameter(GET_CMD, 0, 0)
        return bool(val1)

    def fset(self, enable):
        self._dev.SetAutoParameter(SET_CMD, enable, 0)

    return Facet(fget, fset, type=bool, doc=doc)


class BufferInfo(object):
    def __init__(self, ptr, id):
        self.ptr = ptr
        self.id = id


class UC480_Camera(Camera):
    """A uc480-supported Camera"""
    DEFAULT_KWDS = Camera.DEFAULT_KWDS.copy()
    DEFAULT_KWDS.update(vsub=1, hsub=1)

    def _initialize(self):
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
            The serial number string of the camera
        model : str, optional
            The model of the camera
        """
        self._id = int(self._paramset['id'])
        self._serial = self._paramset['serial']
        self._model = self._paramset['model']

        self._in_use = False
        self._width, self._height = 0, 0
        self._color_depth = 0
        self._color_mode = 0
        self._list_p_img_mem = None
        self._list_memid = None

        self._buffers = []
        self._queue_enabled = False
        self._trigger_mode = lib.SET_TRIGGER_OFF

        self._open()
        self._load_constants()

    def _load_constants(self):
        self._max_master_gain = self._dev.SetHWGainFactor(lib.INQUIRE_MASTER_GAIN_FACTOR, 100) / 100.

        offset_range = self._dev.Blacklevel(lib.BLACKLEVEL_CMD_GET_OFFSET_RANGE)
        self._blacklevel_offset_min = offset_range.s32Min
        self._blacklevel_offset_max = offset_range.s32Max
        self._blacklevel_offset_inc = offset_range.s32Inc

    def __del__(self):
        if self._in_use:
            self.close()  # In case someone forgot to close()

    def set_auto_exposure(self, enable=True):
        """Enable or disable the auto exposure shutter."""
        self._dev.SetAutoParameter(lib.SET_ENABLE_AUTO_SHUTTER, enable, 0)

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
            cmd = lib.PARAMETERSET_CMD_LOAD_EEPROM
            param = ffi.new('char[]', b'/cam/set1')
        else:
            cmd = lib.PARAMETERSET_CMD_LOAD_FILE
            param = ffi.new('wchar_t[]', filename)

        self._dev.ParameterSet(cmd, param, ffi.sizeof(param))
        self._init_colormode()  # Ignore loaded color mode b/c we only support a few

        # Make sure memory is set up for right color depth
        depth_map = {
            lib.CM_MONO8: 8,
            lib.CM_RGBA8_PACKED: 32,
            lib.CM_BGRA8_PACKED: 32
        }
        mode = self._dev.SetColorMode(lib.GET_COLOR_MODE)
        depth = depth_map[mode]
        if depth != self._color_depth:
            log.debug("Color depth changed from %s to %s",
                      self._color_depth, depth)
            num_bufs = len(self._buffers)
            self._free_image_mem_seq()
            self._color_depth = depth
            self._allocate_mem_seq(num_bufs)
        self._color_mode = mode

    def _open(self, num_bufs=1):
        """ Connect to the camera and set up the image memory."""
        self._dev = lib.Camera(self._id, ffi.NULL)
        self._in_use = True
        self._refresh_sizes()
        log.debug('image width=%d, height=%d', self.width, self.height)

        self._init_colormode()
        self._set_AOI(0, 0, self._width, self._height)
        self._allocate_mem_seq(num_bufs)

        self._seq_event = win32event.CreateEvent(None, False, False, '')
        self._frame_event = win32event.CreateEvent(None, True, False, '')  # Don't auto-reset
        self._dev.InitEvent(self._seq_event.handle, lib.SET_EVENT_SEQ)
        self._dev.InitEvent(self._frame_event.handle, lib.SET_EVENT_FRAME)

    def _init_colormode(self):
        log.debug("Initializing default color mode")
        sensor_mode = self._get_sensor_color_mode()
        mode_map = {
            lib.COLORMODE_MONOCHROME: (lib.CM_MONO8, 8),
            lib.COLORMODE_BAYER: (lib.CM_RGBA8_PACKED, 32)
        }
        try:
            mode, depth = mode_map[sensor_mode]
        except KeyError:
            raise Exception("Currently unsupported sensor color mode!")

        self._color_mode = mode
        self._color_depth = depth
        log.debug('color_depth=%d, color_mode=%d', depth, mode)

        self._dev.SetColorMode(self._color_mode)

    def _free_image_mem_seq(self):
        self._dev.ClearSequence()
        for buf in self._buffers:
            self._dev.FreeImageMem(buf.ptr, buf.id)
        self._buffers = []

    def _allocate_mem_seq(self, num_bufs):
        """Create and setup the image memory for live capture."""
        for i in range(num_bufs):
            p_img_mem, memid = self._dev.AllocImageMem(self._width, self._height, self._color_depth)
            self._dev.AddToSequence(p_img_mem, memid)
            self._buffers.append(BufferInfo(p_img_mem, memid))

        # Initialize display
        self._dev.SetDisplayMode(lib.SET_DM_DIB)

    def close(self):
        """Close the camera and release the associated image memory."""
        self._dev.ExitEvent(lib.SET_EVENT_SEQ)
        self._dev.ExitEvent(lib.SET_EVENT_FRAME)

        try:
            self._dev.ExitCamera()
            self._in_use = False
        except Exception as e:
            log.error("Failed to close camera")
            log.error(str(e))

    def _bytes_per_line(self):
        pitch = self._dev.GetImageMemPitch()
        log.debug('bytes_per_line=%d', pitch)
        return pitch

    def _get_max_img_size(self):
        """Max (w,h) of AOI, given current binning and subsampling"""
        size = self._dev.AOI(lib.AOI_IMAGE_GET_SIZE_MAX)
        return size.s32Width, size.s32Height

    def _get_sensor_color_mode(self):
        info = self._dev.GetSensorInfo()
        return char_to_int(info.nColorMode)

    def _array_from_buffer(self, buf):
        h = self.height
        arr = np.frombuffer(buf, np.uint8)

        if self._color_mode == lib.CM_RGBA8_PACKED:
            w = self.bytes_per_line // 4
            arr = arr.reshape((h, w, 4), order='C')[:,:,:3]
        elif self._color_mode == lib.CM_BGRA8_PACKED:
            w = self.bytes_per_line // 4
            arr = arr.reshape((h, w, 4), order='C')[:, :, 2::-1]
        elif self._color_mode == lib.CM_MONO8:
            w = self.bytes_per_line
            arr = arr.reshape((h, w), order='C')
        else:
            raise Error("Unsupported color mode!")
        return arr

    def _set_queueing(self, enable):
        if enable:
            if not self._queue_enabled:
                self._dev.InitImageQueue(0)
        else:
            if self._queue_enabled:
                self._dev.ExitImageQueue()
        self._queue_enabled = enable

    def _set_subsampling(self, vsub, hsub):
        mode = SUBSAMP_V_CODE_FROM_NUM[vsub] | SUBSAMP_H_CODE_FROM_NUM[hsub]
        self._dev.SetSubSampling(mode)

    def _get_subsampling(self):
        vsub = self._dev.SetSubSampling(lib.GET_SUBSAMPLING_FACTOR_VERTICAL)
        hsub = self._dev.SetSubSampling(lib.GET_SUBSAMPLING_FACTOR_HORIZONTAL)
        return vsub, hsub

    def _set_binning(self, vbin, hbin):
        mode = BIN_V_CODE_FROM_NUM[vbin] | BIN_H_CODE_FROM_NUM[hbin]
        self._dev.SetBinning(mode)

    def start_capture(self, **kwds):
        self._handle_kwds(kwds, fill_coords=False)

        self._set_binning(kwds['vbin'], kwds['hbin'])
        self._set_subsampling(kwds['vsub'], kwds['hsub'])
        self._refresh_sizes()

        # Fill coords now b/c max width/height may have changed
        self._handle_kwds(kwds, fill_coords=True)
        self._set_AOI(kwds['left'], kwds['top'], kwds['right'], kwds['bot'])
        self._set_exposure(kwds['exposure_time'])
        self._set_gain(kwds['gain'])

        self._free_image_mem_seq()
        self._allocate_mem_seq(kwds['n_frames'])

        self._set_queueing(True)  # Use queue instead of ring buffer for finite sequence

        if self._trigger_mode == lib.SET_TRIGGER_OFF:
            self._trigger_mode = lib.SET_TRIGGER_SOFTWARE

        self._dev.SetExternalTrigger(self._trigger_mode)
        self._dev.EnableEvent(lib.SET_EVENT_SEQ)
        self._dev.CaptureVideo(lib.DONT_WAIT)  # Trigger

    @check_units(timeout='ms')
    def get_captured_image(self, timeout='1s', copy=True):
        ret = win32event.WaitForSingleObject(self._seq_event, int(timeout.m_as('ms')))
        self._dev.DisableEvent(lib.SET_EVENT_SEQ)

        if ret == win32event.WAIT_TIMEOUT:
            raise TimeoutError
        elif ret != win32event.WAIT_OBJECT_0:
            raise Error("Failed to grab image")

        # Assumes we have exactly as many images as buffers
        arrays = []
        for buf in self._buffers:
            buf_size = self.bytes_per_line * self.height
            array = self._array_from_buffer(ffi.buffer(buf.ptr, buf_size))
            arrays.append(np.copy(array) if copy else array)

        self._dev.StopLiveVideo(lib.WAIT)

        if len(arrays) == 1:
            return arrays[0]
        else:
            return tuple(arrays)

    def grab_image(self, timeout='1s', copy=True, **kwds):
        self.start_capture(**kwds)
        return self.get_captured_image(timeout=timeout, copy=copy)

    @check_units(framerate='?Hz')
    def start_live_video(self, framerate=None, **kwds):
        self._handle_kwds(kwds, fill_coords=False)

        self._set_binning(kwds['vbin'], kwds['hbin'])
        self._set_subsampling(kwds['vsub'], kwds['hsub'])
        self._refresh_sizes()

        # Fill coords now b/c max width/height may have changed
        self._handle_kwds(kwds, fill_coords=True)
        self._set_AOI(kwds['left'], kwds['top'], kwds['right'], kwds['bot'])

        # Framerate should be set *before* exposure time
        if framerate is None:
            # This is necessary to ensure that the exposure_time is within the reachable range
            framerate = 1/Q_(kwds['exposure_time'])
        self._dev.SetFrameRate(framerate.m_as('Hz'))

        self._set_exposure(kwds['exposure_time'])
        self._set_gain(kwds['gain'])

        self._free_image_mem_seq()
        self._allocate_mem_seq(num_bufs=2)
        self._set_queueing(False)

        self._trigger_mode = lib.SET_TRIGGER_OFF
        self._dev.SetExternalTrigger(self._trigger_mode)
        self._dev.EnableEvent(lib.SET_EVENT_FRAME)
        self._dev.CaptureVideo(lib.WAIT)

    def stop_live_video(self):
        self._dev.StopLiveVideo(lib.WAIT)
        self._dev.DisableEvent(lib.SET_EVENT_FRAME)

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
        buf_num, buf_ptr, last_buf_ptr = self._dev.GetActSeqBuf()
        buf_size = self.bytes_per_line * self.height
        array = self._array_from_buffer(ffi.buffer(last_buf_ptr, buf_size))
        return np.copy(array) if copy else array

    def _get_AOI(self):
        rect = self._dev.AOI(lib.AOI_IMAGE_GET_AOI)
        return rect.s32X, rect.s32Y, rect.s32Width, rect.s32Height

    def _set_AOI(self, x0, y0, x1, y1):
        self._dev.AOI(lib.AOI_IMAGE_SET_AOI, (x0, y0, x1-x0, y1-y0))
        self._refresh_sizes()

    def _refresh_sizes(self):
        _, _, self._width, self._height = self._get_AOI()
        self._max_width, self._max_height = self._get_max_img_size()

    @check_units(exp_time='ms')
    def _set_exposure(self, exp_time):
        self._dev.Exposure(lib.IS_EXPOSURE_CMD_SET_EXPOSURE, exp_time.m_as('ms'))

    def _get_exposure(self):
        exp_ms = self._dev.Exposure(lib.IS_EXPOSURE_CMD_GET_EXPOSURE)
        return Q_(exp_ms, 'ms')

    def _get_exposure_inc(self):
        inc_ms = self._dev.Exposure(lib.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_INC)
        return Q_(inc_ms, 'ms')

    def _get_gain(self):
        ignore = lib.IGNORE_PARAMETER
        return self._dev.SetHardwareGain(lib.IS_GET_MASTER_GAIN, ignore, ignore, ignore)

    def _set_gain(self, gain):
        ignore = lib.IGNORE_PARAMETER
        return self._dev.SetHardwareGain(max(min(gain, 100), 0), ignore, ignore, ignore)

    def _last_img_mem(self):
        """Get a ctypes char-pointer to the starting address of the image memory
        last used for image capturing."""
        buf_num, buf_ptr, last_buf_ptr = self._dev.GetActSeqBuf()
        return last_buf_ptr

    def _color_mode_string(self):
        MAP = {
            lib.CM_MONO8: 'mono8',
            lib.CM_MONO16: 'mono16',
        }
        return MAP.get(self._color_mode)

    def set_trigger(self, mode='software', edge='rising'):
        """Set the camera trigger mode.

        Parameters
        ----------
        mode : string
            Either 'off', 'software'(default), or 'hardware'.
        edge : string
            Hardware trigger is either on the 'rising'(default) or 'falling' edge.
        """
        if mode == 'off':
            new_mode = lib.SET_TRIGGER_OFF
        elif mode == 'software':
            new_mode = lib.SET_TRIGGER_SOFTWARE
        elif mode == 'hardware':
            if edge == 'rising':
                new_mode = lib.SET_TRIGGER_LO_HI
            elif edge == 'falling':
                new_mode = lib.SET_TRIGGER_HI_LO
            else:
                raise Error("Trigger edge value {} must be either 'rising' or 'falling'".format(edge))
        else:
            raise Error("Unrecognized trigger mode {}".format(mode))

        ret = lib.is_SetExternalTrigger(self._hcam, new_mode)
        if ret != lib.SUCCESS:
            raise Error("Failed to set external trigger. Return code 0x{:x}".format(ret))
        else:
            self._trigger_mode = new_mode

    def _get_trigger(self):
        """Get the current trigger settings.

        Returns
        -------
        string
            off, hardware or software
        """
        self._trigger_mode = self._dev.SetExternalTrigger(lib.GET_EXTERNALTRIGGER)

        if self._trigger_mode == lib.SET_TRIGGER_OFF:
            return 'off'
        if self._trigger_mode == lib.SET_TRIGGER_SOFTWARE:
            return 'software'
        else:
            return 'hardware'

    def get_trigger_level(self):
        """Get the current hardware trigger level.

        Returns
        -------
        int
            A value of 0 indicates trigger signal is low (not triggered)
        """
        return self._dev.SetExternalTrigger(lib.GET_TRIGGER_STATUS)

    @check_units(delay='?us')
    def set_trigger_delay(self, delay):
        """Set the time to delay a hardware trigger.

        Parameters
        ----------
        delay : ``[time]``-dimensioned Quantity
            The delay time after trigger signal is received to trigger the camera. Has microsecond
            resolution.
        """
        delay_us = 0 if delay is None else int(delay.m_as('us'))
        self._dev.SetTriggerDelay(delay_us)

    def get_trigger_delay(self):
        """Get the trigger delay in ``[time]`` units.

        Returns
        -------
        string
            Trigger delay
        """
        param = self._dev.SetTriggerDelay(lib.GET_TRIGGER_DELAY)
        return Q_(param, 'us')

    @Facet
    def auto_blacklevel(self):
        """Whether auto-blacklevel correction is turned on"""
        mode = self._dev.Blacklevel(lib.BLACKLEVEL_CMD_GET_MODE)
        return bool(mode == lib.AUTO_BLACKLEVEL_ON)

    @auto_blacklevel.setter
    def auto_blacklevel(self, enable):
        caps = self._dev.Blacklevel(lib.BLACKLEVEL_CMD_GET_CAPS)
        if not (caps & lib.BLACKLEVEL_CAP_SET_AUTO_BLACKLEVEL):
            raise UnsupportedFeatureError

        mode = lib.AUTO_BLACKLEVEL_ON if enable else lib.AUTO_BLACKLEVEL_OFF
        self._dev.Blacklevel(lib.BLACKLEVEL_CMD_SET_MODE, mode)

    @Facet(limits=('_blacklevel_offset_min', '_blacklevel_offset_max', '_blacklevel_offset_inc'))
    def blacklevel_offset(self):
        """The blacklevel offset value (an int)"""
        return self._dev.Blacklevel(lib.BLACKLEVEL_CMD_GET_OFFSET)

    @blacklevel_offset.setter
    def blacklevel_offset(self, offset):
        self._dev.Blacklevel(lib.BLACKLEVEL_CMD_SET_OFFSET, offset)

    @Facet(type=int, units='MHz')
    def pixelclock(self):
        return self._dev.PixelClock(lib.PIXELCLOCK_CMD_GET)

    # TODO: Add some bounds checking. This is tricky since the bounds can change based on camera
    # mode. May have to add dynamic limits to Facets if we want to do this within the facet.
    # Otherwise we could either always pull in a new range to check against, or only check the range
    # on an "invalid parameter" error.
    @pixelclock.setter
    def pixelclock(self, clock):
        self._dev.PixelClock(lib.PIXELCLOCK_CMD_SET, clock)

    @Facet(units='MHz')
    def pixelclock_default(self):
        return self._dev.PixelClock(lib.PIXELCLOCK_CMD_GET_DEFAULT)

    @Facet(limits=(1.0, 10.0))
    def gamma(self):
        """The gamma correction value (1.0-10.0)"""
        return self._dev.Gamma(lib.GAMMA_CMD_GET) / 100.

    @gamma.setter
    def gamma(self, gamma):
        gamma_factor = int(round(gamma * 100))
        self._dev.Gamma(lib.GAMMA_CMD_SET, gamma_factor)

    @Facet
    def gain_boost(self):
        """Whether the analog gain boost is enabled

        A change to the gain boost will not affect the very next image captured. It's unclear
        whether this is an inadequacy of Instrumental, or an underlying bug/feature of the library.
        """
        if not self._dev.SetGainBoost(lib.GET_SUPPORTED_GAINBOOST):
            return None
        boost = self._dev.SetGainBoost(lib.GET_GAINBOOST)
        return bool(boost == lib.SET_GAINBOOST_ON)

    @gain_boost.setter
    def gain_boost(self, boost):
        # For some reason, this does not take effect on the next image captured, but the
        # image after that. It is unclear what's causing this.
        if not self._dev.SetGainBoost(lib.GET_SUPPORTED_GAINBOOST):
            raise UnsupportedFeatureError("Camera does not support the gain boost feature")
        val = lib.SET_GAINBOOST_ON if boost else lib.SET_GAINBOOST_OFF
        self._dev.SetGainBoost(val)

    @Facet(limits=(1.0, 'max_master_gain'))
    def master_gain(self):
        """The master gain factor; 1.0 is the lowest gain."""
        gain_factor = self._dev.SetHWGainFactor(lib.GET_MASTER_GAIN_FACTOR, 0)
        return gain_factor / 100.

    @master_gain.setter
    def master_gain(self, gain):
        gain_factor = int(round(gain * 100))
        self._dev.SetHWGainFactor(lib.SET_MASTER_GAIN_FACTOR, gain_factor)

    max_master_gain = property(lambda self: self._max_master_gain,
                               doc="Max value that ``master_gain`` can take")

    auto_gain = AutoParamEnableFacet(
        'AUTO_GAIN',
        doc="Whether auto gain is enabled"
    )
    auto_sensor_gain = AutoParamEnableFacet(
        'AUTO_SENSOR_GAIN',
        doc="Whether sensor-based auto gain is enabled"
    )
    auto_exposure = AutoParamEnableFacet(
        'AUTO_SHUTTER',
        doc="Whether auto exposure is enabled"
    )
    auto_sensor_exposure = AutoParamEnableFacet(
        'AUTO_SENSOR_SHUTTER',
        doc="Whether sensor-based auto exposure is enabled"
    )
    auto_whitebalance = AutoParamEnableFacet(
        'AUTO_WHITEBALANCE',
        doc="Whether auto whitebalance is enabled"
    )
    auto_sensor_whitebalance = AutoParamEnableFacet(
        'AUTO_SENSOR_WHITEBALANCE',
        doc="Whether sensor-based auto whitebalance is enabled"
    )
    auto_framerate = AutoParamEnableFacet(
        'AUTO_FRAMERATE',
        doc="Whether auto framerate is enabled"
    )
    auto_sensor_framerate = AutoParamEnableFacet(
        'AUTO_SENSOR_FRAMERATE',
        doc="Whether sensor-based auto framerate is enabled"
    )

    #: uEye camera ID number. Read-only
    id = property(lambda self: self._id)

    #: Camera serial number string. Read-only
    serial = property(lambda self: self._serial)

    #: Camera model number string. Read-only
    model = property(lambda self: self._model)

    #: Number of bytes used by each line of the image. Read-only
    bytes_per_line = property(lambda self: self._bytes_per_line())

    #: Width of the camera image in pixels
    width = property(lambda self: self._width)
    max_width = property(lambda self: self._max_width)

    #: Height of the camera image in pixels
    height = property(lambda self: self._height)
    max_height = property(lambda self: self._max_height)

    #: Color mode string. Read-only
    color_mode = property(lambda self: self._color_mode_string())

    #: Trigger mode string. Read-only
    trigger_mode = property(lambda self: self._get_trigger())

    #: Current framerate, in ``[time]⁻¹`` units. Read-only
    framerate = property(lambda self: Q_(self._dev.SetFrameRate(lib.GET_FRAMERATE), 'Hz'))
