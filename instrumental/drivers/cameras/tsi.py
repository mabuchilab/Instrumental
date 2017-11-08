# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
from future.utils import PY2

import sys
import os.path
from time import clock
import logging as log

import numpy as np
from cffi import FFI
from enum import Enum

from . import Camera
from ..util import as_enum, unit_mag, check_units
from .. import ParamSet, register_cleanup
from ...errors import Error, TimeoutError
from ... import u

_INST_PARAMS = ['serial', 'number']
_INST_CLASSES = ['TSI_Camera']

if PY2:
    memoryview = buffer  # Needed b/c np.frombuffer is broken on memoryviews in PY2

ffi = FFI()
mod_dir, _ = os.path.split(__file__)
with open(os.path.join(mod_dir, '_tsi', 'tsi.h')) as f:
    ffi.cdef(f.read())
ffi.cdef("""
    #define WAIT_OBJECT_0       0x00L
    #define WAIT_ABANDONED      0x80L
    #define WAIT_TIMEOUT        0x102L
    #define WAIT_FAILED         0xFFFFFFFF
    #define INFINITE            0xFFFFFFFF
    DWORD WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds);
    BOOL ResetEvent(HANDLE hEvent);
""")
lib = ffi.dlopen('tsi_sdk')
winlib = ffi.dlopen('Kernel32.dll')

param_type = {
    lib.TSI_PARAM_ATTR: 'uint8_t*',
    lib.TSI_PARAM_PROTOCOL: 'uint32_t*',
    lib.TSI_PARAM_FW_VER: 'char[64]',
    lib.TSI_PARAM_HW_VER: 'char[64]',
    lib.TSI_PARAM_HW_MODEL: 'char[64]',
    lib.TSI_PARAM_HW_SER_NUM: 'char[64]',
    lib.TSI_PARAM_CAMSTATE: 'uint32_t*',
    lib.TSI_PARAM_CAM_EXPOSURE_STATE: None,
    lib.TSI_PARAM_CAM_TRIGGER_STATE: 'uint32_t*',
    lib.TSI_PARAM_EXPOSURE_UNIT: 'TSI_EXPOSURE_UNITS*',
    lib.TSI_PARAM_EXPOSURE_TIME: 'uint32_t*',
    lib.TSI_PARAM_ACTUAL_EXPOSURE_TIME: 'uint32_t*',
    lib.TSI_PARAM_FRAME_TIME: 'float*',
    lib.TSI_PARAM_VSIZE: 'uint32_t*',
    lib.TSI_PARAM_HSIZE: 'uint32_t*',
    lib.TSI_PARAM_ROI_BIN: 'TSI_ROI_BIN*',
    lib.TSI_PARAM_FRAME_COUNT: 'uint32_t*',
    lib.TSI_PARAM_CURRENT_FRAME: 'uint32_t*',
    lib.TSI_PARAM_OP_MODE: 'TSI_OP_MODE*',
    lib.TSI_PARAM_CDS_GAIN: 'uint32_t*',
    lib.TSI_PARAM_VGA_GAIN: 'uint32_t*',
    lib.TSI_PARAM_GAIN: 'uint32_t*',
    lib.TSI_PARAM_OPTICAL_BLACK_LEVEL: 'uint32_t*',
    lib.TSI_PARAM_PIXEL_OFFSET: 'uint32_t*',
    lib.TSI_PARAM_READOUT_SPEED_INDEX: 'uint32_t*',
    lib.TSI_PARAM_READOUT_SPEED: 'uint32_t*',
    lib.TSI_PARAM_FRAME_RATE: 'float*',
    lib.TSI_PARAM_COOLING_MODE: 'uint32_t*',
    lib.TSI_PARAM_COOLING_SETPOINT: 'int32_t*',
    lib.TSI_PARAM_TEMPERATURE: 'int32_t*',
    lib.TSI_PARAM_QX_OPTION_MODE: 'uint32_t*',
    lib.TSI_PARAM_TURBO_CODE_MODE: 'uint32_t*',
    lib.TSI_PARAM_XORIGIN: 'uint32_t*',
    lib.TSI_PARAM_YORIGIN: 'uint32_t*',
    lib.TSI_PARAM_XPIXELS: 'uint32_t*',
    lib.TSI_PARAM_YPIXELS: 'uint32_t*',
    lib.TSI_PARAM_XBIN: 'uint32_t*',
    lib.TSI_PARAM_YBIN: 'uint32_t*',
    #lib.TSI_PARAM_IMAGE_ACQUISTION_MODE: 'uint32_t*',
    lib.TSI_PARAM_NAMED_VALUE: 'char[128]',
    lib.TSI_PARAM_TAPS_INDEX: 'uint32_t*',
    lib.TSI_PARAM_TAPS_VALUE: 'uint32_t*',
    #lib.TSI_PARAM_RESERVED_1: None,
    #lib.TSI_PARAM_RESERVED_2: None,
    #lib.TSI_PARAM_RESERVED_3: None,
    #lib.TSI_PARAM_RESERVED_4: None,
    lib.TSI_PARAM_GLOBAL_CAMERA_NAME: 'char[64]',
    lib.TSI_PARAM_CDS_GAIN_VALUE: 'uint32_t*',
    lib.TSI_PARAM_PIXEL_SIZE: 'float*',
    lib.TSI_PARAM_READOUT_TIME: 'float*',
    lib.TSI_PARAM_HW_TRIGGER_ACTIVE: 'uint32_t*',
    lib.TSI_PARAM_HW_TRIG_SOURCE: 'TSI_HW_TRIG_SOURCE*',
    lib.TSI_PARAM_HW_TRIG_POLARITY: 'TSI_HW_TRIG_POLARITY*',
    lib.TSI_PARAM_TAP_BALANCE_ENABLE: 'uint32_t*',
    lib.TSI_PARAM_DROPPED_FRAMES: 'uint32_t*',
    lib.TSI_PARAM_EXPOSURE_TIME_US: 'uint32_t*',
    #lib.TSI_PARAM_RESERVED_5: None,
    #lib.TSI_PARAM_RESERVED_6: None,
    #lib.TSI_PARAM_RESERVED_7: None,
    lib.TSI_PARAM_UPDATE_PARAMETERS: 'uint32_t*',
    #lib.TSI_PARAM_FEATURE_LIST: None,
    #lib.TSI_PARAM_FEATURE_VALID: None,
    lib.TSI_PARAM_NUM_IMAGE_BUFFERS: 'int32_t*',
    lib.TSI_PARAM_COLOR_FILTER_TYPE: 'char[32]',
    #lib.TSI_PARAM_COLOR_FILTER_PHASE: '',
    #lib.TSI_PARAM_IR_FILTER_TYPE: '',
    #lib.TSI_PARAM_COLOR_CAMERA_CORRECTION_MATRIX: None,
    #lib.TSI_PARAM_CCM_OUTPUT_COLOR_SPACE: None,
    #lib.TSI_PARAM_DEFAULT_WHITE_BALANCE_MATRIX: None,
    lib.TSI_PARAM_USB_ENABLE_LED: 'uint32_t*',
}


def from_enum(item):
    return item._value_ if isinstance(item, Enum) else item


def _strip_prefix(value, prefix):
    return value[len(prefix):] if value.startswith(prefix) else value


enum_map = {}


if 'sphinx' in sys.modules:
    class make_enum(object):
        def __init__(self, *args):
            pass
        def __getattr__(self, name):
            return name
else:
    def make_enum(name, c_name, prefix=''):
        ctype = ffi.typeof(c_name)
        d = {_strip_prefix(v, prefix):k for k,v in ctype.elements.items()}
        new_enum = Enum(name, d)
        enum_map[c_name] = new_enum
        return new_enum


Param = make_enum('Param', 'TSI_PARAM_ID', 'TSI_PARAM_')
ExpUnit = make_enum('ExpUnit', 'TSI_EXPOSURE_UNITS', 'TSI_EXP_UNIT_')
Status = make_enum('Status', 'TSI_CAMERA_STATUS', 'TSI_STATUS_')
AcqStatus = make_enum('AcqStatus', 'TSI_ACQ_STATUS_ID', 'TSI_ACQ_STATUS_')
TrigSource = make_enum('TrigSource', 'TSI_HW_TRIG_SOURCE', 'TSI_HW_TRIG_')
TrigPol = make_enum('TrigPol', 'TSI_HW_TRIG_POLARITY', 'TSI_HW_TRIG_')
OpMode = make_enum('OpMode', 'TSI_OP_MODE', 'TSI_OP_MODE_')


class TSI_DLL_SDK(object):
    def __init__(self):
        self._ll = lib.tsi_create_sdk()

    def destroy(self):
        log.info("Destroying TSI_DLL_SDK")
        self.Close()
        lib.tsi_destroy_sdk(self._ll)

    def Open(self):
        self._ll.vptr.Open(self._ll)

    def Close(self):
        log.info("Closing TSI_DLL_SDK")
        self._ll.vptr.Close(self._ll)

    def GetNumberOfCameras(self):
        return self._ll.vptr.GetNumberOfCameras(self._ll)

    def GetCamera(self, camera_number):
        cam_ptr = self._ll.vptr.GetCamera(self._ll, camera_number)
        if cam_ptr == ffi.NULL:
            raise Error("Camera not found. Make sure you called GetNumberOfCameras first")
        return TSI_DLL_Camera(cam_ptr)

    def GetCameraInterfaceTypeStr(self, camera_number):
        ret = self._ll.vptr.GetCameraInterfaceTypeStr(self._ll, camera_number)
        if ret == ffi.NULL:
            raise Error("Camera not found. Make sure you called GetNumberOfCameras first")
        return ffi.string(ret)

    def GetCameraAddressStr(self, camera_number, address_select):
        ret = self._ll.vptr.GetCameraAddressStr(self._ll, camera_number, address_select)
        if ret == ffi.NULL:
            raise Error("Camera not found, or invalid address_select value for this camera. "
                        "Make sure you called GetNumberOfCameras first")
        return ffi.string(ret)

    def GetCameraName(self, camera_number):
        ret = self._ll.vptr.GetCameraName(self._ll, camera_number)
        if ret == ffi.NULL:
            raise Error("Camera not found. Make sure you called GetNumberOfCameras first")
        return ffi.string(ret)

    def GetCameraSerialNumStr(self, camera_number):
        ret = self._ll.vptr.GetCameraSerialNumStr(self._ll, camera_number)
        if ret == ffi.NULL:
            raise Error("Camera not found. Make sure you called GetNumberOfCameras first")
        return ffi.string(ret)


sdk = TSI_DLL_SDK()
sdk.Open()
register_cleanup(sdk.destroy)


class TSI_DLL_Camera(object):
    def __init__(self, ptr):
        self._ll = ptr

    def Open(self):
        success = self._ll.vptr.Open(self._ll)
        if not success:
            raise Exception("Opening camera failed")

    def Close(self):
        log.info("Closing TSI_DLL_Camera")
        success = self._ll.vptr.Close(self._ll)
        if not success:
            raise Exception("Closing camera failed")

    def Status(self):
        p_status = ffi.new('TSI_CAMERA_STATUS*')
        success = self._ll.vptr.Status(self._ll, p_status)
        if not success:
            raise Exception("Failed to get camera status")
        return Status(p_status[0])

    def GetCameraName(self):
        return ffi.string(self._ll.vptr.GetCameraName(self._ll))

    def SetCameraName(self, name):
        success = self._ll.vptr.SetCameraName(self._ll, name)
        if not success:
            raise Exception("Setting camera name failed")

    def GetDataTypeSize(self, data_type):
        return self._ll.vptr.GetDataTypeSize(self._ll, data_type)

    def _param_data_type(self, param_id):
        p_data = ffi.new('TSI_DATA_TYPE*')
        self._ll.vptr.GetParameter(self._ll, lib.TSI_ATTR_DATA_TYPE, ffi.sizeof('TSI_DATA_TYPE'),
                                   p_data)
        return p_data[0]

    def GetParameter(self, param_id):
        param_id = from_enum(param_id)
        ctype = ffi.typeof(param_type[param_id])

        if ctype.kind == 'pointer':
            size = ffi.sizeof(ctype.item)
        else:
            size = ffi.sizeof(ctype)

        p_data = ffi.new(ctype)
        success = self._ll.vptr.GetParameter(self._ll, param_id, size, p_data)
        if not success:
            raise Exception("Failed to get camera parameter")

        if param_type[param_id].startswith('char'):
            return ffi.string(p_data)
        elif ctype.kind == 'enum':
            return enum_map[ctype.cname](p_data[0])
        else:
            return p_data[0]

    def SetParameter(self, param_id, data):
        param_id = from_enum(param_id)
        data = from_enum(data)

        ctype = ffi.typeof(param_type[param_id])
        if ctype.kind == 'array':
            p_data = data
        else:
            p_data = ffi.new(ctype, data)
        success = self._ll.vptr.SetParameter(self._ll, param_id, p_data)
        if not success:
            raise Exception("Failed to set camera parameter")

    def ResetCamera(self):
        ok = self._ll.vptr.ResetCamera(self._ll)
        if not ok:
            raise Exception("Failed to reset camera")

    def FreeImage(self, image):
        ok = self._ll.vptr.FreeImage(self._ll, image)
        if not ok:
            raise Exception("Failed to free image")

    def StartAndWait(self, timeout_ms):
        ok = self._ll.vptr.StartAndWait(self._ll, timeout_ms)
        if not ok:
            raise Exception("Failed to start capture. Current camera parameters do not permit "
                            "operation of the camera.")

    def Start(self):
        ok = self._ll.vptr.Start(self._ll)
        if not ok:
            raise Exception("Failed to start capture")

    def Stop(self):
        ok = self._ll.vptr.Stop(self._ll)
        if not ok:
            raise Exception("Failed to stop capture")

    def GetAcquisitionStatus(self):
        return AcqStatus(self._ll.vptr.GetAcquisitionStatus(self._ll))

    def GetExposeCount(self):
        # This appears to always return zero
        return self._ll.vptr.GetExposeCount(self._ll)

    def GetFrameCount(self):
        return self._ll.vptr.GetFrameCount(self._ll)

    def WaitForImage(self, timeout_ms=-1):
        return self._ll.vptr.WaitForImage(self._ll, timeout_ms)

    def ResetExposure(self):
        return self._ll.vptr.ResetExposure(self._ll)

    def GetErrorCode(self):
        return self._ll.vptr.GetErrorCode(self._ll)

    def ClearError(self):
        ok = self._ll.vptr.ClearError(self._ll)
        if not ok:
            raise Exception("Failed to clear error")

    def GetErrorStr(self, code):
        ptr_size = ffi.new('int*', 256)
        buf = ffi.new('char[]', ptr_size[0])
        ok = self._ll.vptr.GetErrorStr(self._ll, code, buf, ptr_size)
        if not ok:
            raise Exception("Failed to get error string")
        return ffi.string(buf)

    def GetLastErrorStr(self):
        msg = self._ll.vptr.GetLastErrorStr(self._ll)
        return ffi.string(msg)

    def GetPendingImage(self):
        return self._ll.vptr.GetPendingImage(self._ll)


def _rw_property(param):
    def fget(self):
        return self._get_parameter(param)

    def fset(self, value):
        self._set_parameter(param, value)

    return property(fget, fset)


def _ro_property(param):
    def fget(self):
        return self._get_parameter(param)
    return property(fget)


class TSI_Camera(Camera):
    DEFAULT_KWDS = Camera.DEFAULT_KWDS.copy()
    DEFAULT_KWDS.update(trig='auto', rising=True)

    class TriggerMode(Enum):
        auto = OpMode.NORMAL
        """Auto-trigger as fast as possible once capture has started"""
        software = auto
        """Alias for `auto`"""
        hw_edge = OpMode.TOE
        """Trigger a single exposure on an edge, using a software-defined exposure time"""
        hw_bulb = OpMode.PDX
        """Trigger a single exposure on an edge of a pulse, and stop the exposure at the end of the
        pulse
        """

    def _initialize(self):
        sdk.GetNumberOfCameras()
        self._partial_sequence = []
        self._next_frame_idx = 0
        self._tot_frames = None  # Zero means 'infinite' capture
        self._trig_mode = None
        self._dev = sdk.GetCamera(self._paramset.get('number', 0))

        if self._dev.Status() != Status.CLOSED:
            raise Error("Camera is already open")

        self._dev.Open()
        self._set_parameter(Param.EXPOSURE_UNIT, ExpUnit.MILLISECONDS)

    def close(self):
        log.info('Closing TSI camera...')
        self._dev.Stop()
        self._dev.Close()

    def _get_parameter(self, param_id):
        return self._dev.GetParameter(param_id)

    def _set_parameter(self, param_id, data):
        self._dev.SetParameter(param_id, data)

    @check_units(exp_time='ms')
    def _set_exposure_time(self, exp_time):
        time_ms = int(exp_time.m_as('ms'))
        self._set_parameter(Param.EXPOSURE_TIME, time_ms)

    def _get_exposure_time(self):
        return self._get_parameter(Param.EXPOSURE_TIME) * u.ms

    def _set_ROI(self, params):
        roi_data = {
            'XOrigin': params['left'],
            'YOrigin': params['top'],
            'XPixels': params['right'] - params['left'],
            'YPixels': params['bot'] - params['top'],
            'XBin': params['hbin'],
            'YBin': params['vbin'],
        }
        self._set_parameter(Param.ROI_BIN, roi_data)

    def _get_ROI(self):
        return self._get_parameter(Param.ROI_BIN)

    def _set_n_frames(self, n_frames):
        # Ensure only one exposure per HW edge trigger
        if self._trig_mode == self.TriggerMode.hw_edge:
            n_frames = 1
        self._set_parameter(Param.FRAME_COUNT, n_frames)

    def grab_image(self, timeout='1s', copy=True, **kwds):
        self.start_capture(**kwds)
        try:
            images = self.get_captured_image(timeout=timeout, copy=copy, **kwds)
        finally:
            self._dev.Stop()
        return images

    def cancel_capture(self):
        """Cancel a capture sequence, cleaning up and stopping the camera"""
        self._dev.Stop()

    @check_units(timeout='?ms')
    def get_captured_image(self, timeout='1s', copy=True, wait_for_all=True, **kwds):
        image_arrs = []

        if self._tot_frames and self._next_frame_idx >= self._tot_frames:
            raise Error("No capture initiated. You must first call start_capture()")

        start_time = clock() * u.s
        while self._next_frame_idx < self._tot_frames:
            if timeout is None:
                frame_ready = self.wait_for_frame(timeout=None)
            else:
                elapsed_time = clock() * u.s - start_time
                frame_ready = self.wait_for_frame(timeout - elapsed_time)

            if not frame_ready:
                if wait_for_all or not image_arrs:
                    self._partial_sequence.extend(image_arrs)  # Save for later
                    raise TimeoutError("Timed out while waiting for image readout")
                else:
                    break

            array = self.latest_frame(copy)
            image_arrs.append(array)
        image_arrs = self._partial_sequence + image_arrs

        if self._tot_frames and self._next_frame_idx >= self._tot_frames:
            self._dev.Stop()
            self._partial_sequence = []

        if len(image_arrs) == 1:
            return image_arrs[0]
        else:
            return tuple(image_arrs)

    def start_capture(self, **kwds):
        self._handle_kwds(kwds)

        self._set_ROI(kwds)
        self._set_exposure_time(kwds['exposure_time'])
        self._set_trig_mode(kwds['trig'], kwds['rising'])
        self._set_n_frames(kwds['n_frames'])
        self._tot_frames = kwds['n_frames']
        self._partial_sequence = []
        self._next_frame_idx = 0

        self._dev.Stop()  # Ensure old captures are finished
        self._dev.Start()

    @unit_mag(timeout='?s')
    def wait_for_frame(self, timeout=None):
        timeout_s = timeout
        start_time = clock()

        while True:
            img = self._dev.GetPendingImage()
            if img != ffi.NULL:
                self._latest_tsi_img = img
                self._next_frame_idx += 1
                return True

            elapsed_time = clock() - start_time
            if timeout_s is not None and elapsed_time > timeout_s:
                return False

    def latest_frame(self, copy=True):
        # Frees the TSI image buffer if `copy` is true. Otherwise, it's the user's responsibility
        # If no buffers are available for use, the frame count will never increment, and
        # wait_for_frame will block (until its timeout is reached)
        img = self._arr_from_img_struct(self._latest_tsi_img, copy)
        self._dev.FreeImage(self._latest_tsi_img)
        return img

    def _arr_from_img_struct(self, tsi_img, copy):
        p_buf = tsi_img.m_PixelData.ui16
        # Note: m_SizeInBytes doesn't seem to work correctly
        frame_size = tsi_img.m_Width * tsi_img.m_Height * tsi_img.m_BytesPerPixel
        self._tsi_img = tsi_img

        if copy:
            image_buf = memoryview(ffi.buffer(p_buf, frame_size)[:])
        else:
            image_buf = memoryview(ffi.buffer(p_buf, frame_size))

        # Convert to array (currently assumes mono16)
        array = np.frombuffer(image_buf, np.uint16)
        array = array.reshape((tsi_img.m_Height, tsi_img.m_Width))

        return array

    def start_live_video(self, **kwds):
        self._handle_kwds(kwds)

        self._set_ROI(kwds)
        self._set_trig_mode(self.TriggerMode.auto)
        self._set_exposure_time(kwds['exposure_time'])
        self._set_n_frames(0)
        self._tot_frames = 0
        self._next_frame_idx = 0

        self._dev.Stop()  # Ensure old captures are finished
        self._dev.Start()

    def stop_live_video(self):
        self._dev.Stop()

    def _set_trig_mode(self, mode, rising=True):
        self._trig_mode = mode = as_enum(self.TriggerMode, mode)
        use_hw_trigger = (mode != self.TriggerMode.auto)
        trig_source = mode.value
        polarity = TrigPol.ACTIVE_HIGH if rising else TrigPol.ACTIVE_LOW

        self._set_parameter(Param.HW_TRIGGER_ACTIVE, use_hw_trigger)
        self._set_parameter(Param.OP_MODE, trig_source)
        self._set_parameter(Param.HW_TRIG_POLARITY, polarity)

    @property
    def name(self):
        return self._dev.GetCameraName()

    @name.setter
    def name(self, name):
        self._dev.SetCameraName(name)

    @property
    def max_width(self):
        sensor_width = self._get_parameter(Param.HSIZE)
        xbin = self._get_parameter(Param.XBIN)
        return sensor_width // xbin

    @property
    def max_height(self):
        sensor_height = self._get_parameter(Param.VSIZE)
        ybin = self._get_parameter(Param.YBIN)
        return sensor_height // ybin

    model = _ro_property(Param.HW_MODEL)
    serial = _ro_property(Param.HW_SER_NUM)
    led_on = _rw_property(Param.USB_ENABLE_LED)

    width = _rw_property(Param.XPIXELS)
    height = _rw_property(Param.YPIXELS)


def list_instruments():
    cameras = []
    for i in range(sdk.GetNumberOfCameras()):
        cam_ser = sdk.GetCameraSerialNumStr(i)
        params = ParamSet(TSI_Camera, serial=cam_ser, number=i)
        cameras.append(params)
    return cameras
