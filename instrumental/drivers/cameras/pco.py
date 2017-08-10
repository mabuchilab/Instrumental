# -*- coding: utf-8 -*-
# Copyright 2015-2017 Nate Bogdanowicz
"""
Driver for PCO cameras that use the PCO.camera SDK.
"""
from future.utils import PY2

import os
import os.path
import tempfile
from enum import Enum
from time import clock
import logging as log

import numpy as np
from cffi import FFI, cparser
from pycparser import CParser
from nicelib import NiceLib, NiceObjectDef

from ._pixelfly import errortext
from . import Camera
from ..util import as_enum, unit_mag, check_units
from .. import ParamSet
from ...errors import Error, TimeoutError
from ... import Q_, u

if PY2:
    memoryview = buffer  # Needed b/c np.frombuffer is broken on memoryviews in PY2

_INST_PRIORITY = 9  # This driver is very slow
_INST_PARAMS = ['number', 'interface']
_INST_CLASSES = ['PCO_Camera']

__all__ = ['PCO_Camera']


# Notes:
# Had to add SC2_Cam.dll, sc2_cl_me4.dll (MUST BE 64-bit versions, can find these in CamView's
# folder)
# Had to fuse a bunch of header files together, manually add some typedefs, preprocess this, append
# some #defines that don't get preprocessed, save to clean.h, and open this with cffi
# It may make sense to do some simple regex-style parsing of the header files to parse out the
# #defines that we care about
# Also, I'm using the errortext module I compiled for the pixelfly library. Still unsure whether I
# should code my own version in Python so we don't require the end-user to compile it.


# Hack to prevent lextab.py and yacctab.py from littering the working directory
tmp_dir = os.path.join(tempfile.gettempdir(), 'instrumental_pycparser')
if not os.path.exists(tmp_dir):
    os.mkdir(tmp_dir)
cparser._parser_cache = CParser(taboutputdir=tmp_dir)

ffi = FFI()
with open(os.path.join(os.path.dirname(__file__), '_pco', 'clean.h')) as f:
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
lib = ffi.dlopen('SC2_Cam.dll')
winlib = ffi.dlopen('Kernel32.dll')


def get_error_text(ret_code):
    pbuf = errortext.ffi.new('char[]', 1024)
    errortext.lib.PCO_GetErrorText(errortext.ffi.cast('unsigned int', ret_code), pbuf, len(pbuf))
    return errortext.ffi.string(pbuf)


class NicePCO(NiceLib):
    def _ret(code):
        if code != 0:
            e = Error(get_error_text(code))
            e.code = code & 0xFFFFFFFF
            raise e

    def _struct_maker(*args):
        """PCO makes you fill in the wSize field of every struct"""
        struct_p = ffi.new(*args)
        struct_p[0].wSize = ffi.sizeof(struct_p[0])
        for name, field in ffi.typeof(struct_p[0]).fields:
            # Only goes one level deep for now
            if field.type.kind == 'struct':
                s = getattr(struct_p[0], name)
                s.wSize = ffi.sizeof(s)
        return struct_p

    _ffi = ffi
    _ffilib = lib
    _prefix = 'PCO_'

    OpenCamera = ('inout', 'ignore')
    OpenCameraEx = ('inout', 'inout')

    # Special cases
    def _GetTransferParameter(hcam, niceobj=None):
        params_p = ffi.new('PCO_SC2_CL_TRANSFER_PARAM *')
        void_p = ffi.cast('void *', params_p)
        lib.PCO_GetTransferParameter(hcam, void_p, ffi.sizeof(params_p[0]))
        # Should do error checking...
        return params_p[0]

    def _SetTransferParametersAuto(hcam, niceobj=None):
        lib.PCO_SetTransferParametersAuto(hcam, ffi.NULL, 0)
        # Should do error checking...

    Camera = NiceObjectDef({
        'CloseCamera': ('in'),
        'GetSizes': ('in', 'out', 'out', 'out', 'out'),
        'SetROI': ('in', 'in', 'in', 'in', 'in'),
        'GetROI': ('in', 'out', 'out', 'out', 'out'),
        'GetInfoString': ('in', 'in', 'buf', 'len'),
        'GetCameraName': ('in', 'buf40', 'len'),
        'GetRecordingState': ('in', 'out'),
        'SetRecordingState': ('in', 'in'),
        'SetDelayExposureTime': ('in', 'in', 'in', 'in', 'in'),
        'GetDelayExposureTime': ('in', 'out', 'out', 'out', 'out'),
        'SetFrameRate': ('in', 'out', 'in', 'inout', 'inout'),
        'GetFrameRate': ('in', 'out', 'out', 'out'),
        'ArmCamera': ('in'),
        'SetBinning': ('in', 'in', 'in'),
        'GetBinning': ('in', 'out', 'out'),
        'GetActiveLookupTable': ('in', 'out', 'out'),
        'SetActiveLookupTable': ('in', 'inout', 'inout'),
        'GetPixelRate': ('in', 'out'),
        # GetTransferParameter = ('in', 'buf', 'len')
        'GetTriggerMode': ('in', 'out'),
        'SetTriggerMode': ('in', 'in'),
        'ForceTrigger': ('in', 'out'),
        'AllocateBuffer': ('in', 'inout', 'in', 'inout', 'inout'),
        'CamLinkSetImageParameters': ('in', 'in', 'in'),
        'FreeBuffer': ('in', 'in'),
        'CancelImages': ('in'),
        'AddBufferEx': ('in', 'in', 'in', 'in', 'in', 'in', 'in'),
        'GetBufferStatus': ('in', 'in', 'out', 'out'),
        'GetLookupTableInfo': ('in', 'in', 'out', 'buf20', 'len', 'out', 'out', 'out', 'out'),
        'GetCameraDescription': ('in', 'out'),
        'EnableSoftROI': ('in', 'in', 'in', 'in'),
        'GetHWIOSignalDescriptor': ('in', 'in', 'out'),
        'GetHWIOSignal': ('in', 'in', 'out'),
        'SetHWIOSignal': ('in', 'in', 'in'),
        'GetIRSensitivity': ('in', 'out'),
        'SetIRSensitivity': ('in', 'in'),
        'GetTransferParameter': _GetTransferParameter,
        'SetTransferParametersAuto': _SetTransferParametersAuto,
    })


class BufferInfo(object):
    def __init__(self, num, address, event):
        self.num = num
        self.address = address
        self.event = event


class PCO_Camera(Camera):
    DEFAULT_KWDS = Camera.DEFAULT_KWDS.copy()
    DEFAULT_KWDS.update(trig='software', rising=True)

    def _initialize(self):
        self.buffers = []
        self.queue = []
        self._partial_sequence = []
        self._buf_size = 0
        self.shutter = None
        self._trig_mode = self.TriggerMode.software

        self._open(self._paramset.get('cam_num', 0))
        self._paramset['interface'] = self.interface_type
        self._paramset['number'] = self.cam_num

        # Flags indicating changed data, i.e. invalid cached data
        self._sizes_changed = True
        self._transfer_param_changed = True
        self._cached_cam_desc = None

        _, _, max_width, max_height = self._get_sizes()
        self._set_ROI(0, 0, max_width, max_height)


    # Enums
    class FrameRateMode(Enum):
        auto = 0
        framerate = 1
        exposure = 2
        strict = 3

    class TriggerMode(Enum):
        auto = 0
        software = 1
        extern_edge = 2
        extern_pulse = 3

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def set_trigger_mode(self, mode, rising=True):
        """Set the trigger mode

        Parameters
        ----------
        mode : `PCO_Camera.TriggerMode` or str
            auto - Exposures occur as fast as possible
            software - Software trigger only
            extern_edge - Software trigger or external hardware trigger on a signal's edge
            extern_pulse - Hardware trigger; delay and exposure are determined by the pulse length
        """
        self._trig_mode = as_enum(self.TriggerMode, mode)
        self._cam.SetTriggerMode(self._trig_mode.value)

        struct = self._cam.GetHWIOSignal(0)
        struct.wPolarity = 0x04 if rising else 0x08
        self._cam.SetHWIOSignal(0, ffi.addressof(struct))

    def _open(self, cam_num):
        openStruct_p = ffi.new('PCO_OpenStruct *')
        openStruct = openStruct_p[0]
        openStruct.wSize = ffi.sizeof('PCO_OpenStruct')
        openStruct.wInterfaceType = self._paramset.get('interface', 0xFFFF)
        openStruct.wCameraNumber = cam_num
        openStruct.wCameraNumAtInterface = 0
        openStruct.wOpenFlags[0] = 0

        try:
            log.info("Opening PCO camera")
            hcam = NicePCO.OpenCameraEx(ffi.NULL, openStruct_p)[0]
        except Error:
            # TODO: Figure out how to reset this error so we can turn on the camera and
            # retry instead of having to restart python. We may need to close the DLL
            # and reopen it, but that's currently difficult/impossible with cffi
            raise Error("Could not find PCO camera. Is it connected and turned on?")

        self._cam = NicePCO.Camera(hcam)

        self.cam_num = openStruct.wCameraNumber
        self.interface_type = openStruct.wInterfaceType

    def close(self):
        """Close the camera"""
        self._cam.SetRecordingState(0)
        self._clear_queue()
        self._free_buffers()
        self._cam.CloseCamera()

    def _enable_soft_roi(self, enable):
        self._cam.EnableSoftROI(enable, ffi.NULL, 0)

    def _get_camera_description(self):
        if not self._cached_cam_desc:
            self._cached_cam_desc = self._cam.GetCameraDescription()
        return self._cached_cam_desc

    @unit_mag(delay='ns', exposure='ns')
    def _set_delay_exposure_time(self, delay, exposure):
        delay_ns = int(round(delay))
        exposure_ns = int(round(exposure))
        self._cam.SetDelayExposureTime(delay_ns, exposure_ns, 0, 0)

    def _get_delay_exposure_time(self):
        delay, exp, delay_timebase, exp_timebase = self._cam.GetDelayExposureTime()
        TIME_MAP = {0: 'ns', 1: 'us', 2: 'ms'}
        delay = Q_(delay, TIME_MAP[delay_timebase])
        exp = Q_(exp, TIME_MAP[exp_timebase])
        return delay, exp

    @unit_mag(framerate='mHz', exposure='ns', ret=(None, 'mHz', 'ns'))
    def _set_framerate(self, framerate, exposure='10ms', priority='auto'):
        exposure_ns = int(round(exposure))
        framerate_mHz = int(round(framerate))
        mode = as_enum(self.FrameRateMode, priority)

        self._cam.ArmCamera()
        status, framerate_mHz, exposure_ns = self._cam.SetFrameRate(mode.value, framerate_mHz,
                                                                    exposure_ns)
        return status, framerate_mHz, exposure_ns

    def _framerate(self):
        status, framerate_mHz, exposure_ns = self._cam.GetFrameRate()
        return Q_(framerate_mHz, 'mHz').to('Hz')

    def _set_ROI(self, x0, y0, x1, y1):
        # Can't figure out how to get Soft ROI working properly, so here we implement it by hand
        desc = self._get_camera_description()
        hstep = desc.wRoiHorStepsDESC
        vstep = desc.wRoiVertStepsDESC

        if x1 <= x0:
            raise Error("ROI must have x1 > x0")
        if y1 <= y0:
            raise Error("ROI must have y1 > y0")

        # Ensure coords are bounded properly
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.max_width, x1)
        y1 = min(self.max_width, y1)

        # Round and center x coords (must be symmetric in dual-ADC mode)
        cx = self.max_width // 2
        xdiff = max(cx - x0, x1 - cx) - 1
        xdiff = (xdiff // hstep + 1) * hstep
        fx0 = cx - xdiff
        fx1 = cx + xdiff

        # Round and center y coords (must be symmetric for pco.edge)
        cy = self.max_height // 2
        ydiff = max(cy - y0, y1 - cy) - 1
        ydiff = (ydiff // vstep + 1) * vstep
        fy0 = cy - ydiff
        fy1 = cy + ydiff

        # Save for later
        self._soft_width = x1 - x0
        self._soft_height = y1 - y0
        self._roi_trim_left = x0 - fx0
        self._roi_trim_top = y0 - fy0

        try:
            self._cam.SetROI(fx0+1, fy0+1, fx1, fy1)
        except Error as e:
            if e.code == 0xA00A3001:
                raise Error("ROI coordinates out of range; asked for x0,y0 = {},{} and x1,y1 = {},{}.\n"
                            "However, x0 must be in the range [0, {}], and x1 must be in the range"
                            " [x0+1, {}]; y0 must be in [0, {}] and y1 must be in [y0+1, {}]".format(
                                x0, y0, x1, y1, self.max_width-1, self.max_width,
                                self.max_height-1, self.max_height))
            raise
        self._sizes_changed = True

    def _get_ROI(self):
        x0, y0, x1, y1 = self._cam.GetROI()
        return x0-1, y0-1, x1, y1

    def _set_centered_ROI(self, width, height):
        _, _, max_width, max_height = self._get_sizes()
        x0 = (max_width-width)//2
        y0 = (max_height-height)//2
        self._set_ROI(x0, y0, x0+width, y0+height)

    def _get_lookup_table_info(self):
        i = 0
        n_luts = 10
        info = []
        while i < n_luts:
            n_luts, desc, id, in_width, out_width, format = self._cam.GetLookupTableInfo(i)
            info.append((desc, id, in_width, out_width, format))
            i += 1
        return info

    def _data_depth(self):
        """The depth of the data format that will be transferred to the PC's buffer"""
        info = self._get_transfer_parameter()
        dataformat = info.DataFormat & lib.PCO_CL_DATAFORMAT_MASK
        depth_map = {
            lib.PCO_CL_DATAFORMAT_5x16:  16,
            lib.PCO_CL_DATAFORMAT_5x12L: 16,
            lib.PCO_CL_DATAFORMAT_5x12:  12,
            lib.PCO_CL_DATAFORMAT_5x12R: 12,
            lib.PCO_CL_DATAFORMAT_10x8:   8,
        }
        if dataformat not in depth_map:
            raise Exception("Unrecognized dataformat {}".format(dataformat))

        return depth_map[dataformat]

    def _get_pixelrate(self):
        pixelrate = self._cam.GetPixelRate()
        return Q_(pixelrate, 'Hz').to('MHz')

    def _get_transfer_parameter(self):
        if self._transfer_param_changed:
            self._cached_transfer_param = self._cam.GetTransferParameter()
            self._transfer_param_changed = False
        return self._cached_transfer_param

    def _get_sizes(self):
        if self._sizes_changed:
            x_act, y_act, x_max, y_max = self._cam.GetSizes()
            self._cached_sizes = x_act, y_act, x_max, y_max
            self._sizes_changed = False
        return self._cached_sizes

    def _find_good_data_format(self, image_width):
        if self._get_pixelrate() < Q_(96, 'MHz'):
            format = lib.PCO_CL_DATAFORMAT_5x16
        else:
            if image_width <= 1920:
                format = lib.PCO_CL_DATAFORMAT_5x16
            else:
                format = lib.PCO_CL_DATAFORMAT_5x12
        return format

    def _allocate_buffers(self, nbufs=None):
        if nbufs is None:
            if len(self.buffers) > 1:
                nbufs = len(self.buffers)
            elif self.shutter == 'continuous':
                nbufs = 2
            else:
                nbufs = 1

        # Clean up existing buffers
        self._cam.SetRecordingState(0)
        self._clear_queue()
        self._free_buffers()

        self._buf_size = self._frame_size()

        # Allocate new buffers
        for i in range(nbufs):
            bufnum, buf_p, event = self._cam.AllocateBuffer(-1, self._buf_size, ffi.NULL, ffi.NULL)
            self.buffers.append(BufferInfo(bufnum, buf_p, event))

    def _free_buffers(self):
        for buf in self.buffers:
            self._cam.FreeBuffer(buf.num)
        self.buffers = []

    def _clear_queue(self):
        self.queue = []
        self._cam.CancelImages()

    def _push_on_queue(self, buf):
        width, height, _, _ = self._get_sizes()
        depth = self._data_depth()
        self._cam.AddBufferEx(0, 0, buf.num, width, height, depth)
        self.queue.append(buf)

    def _frame_size(self):
        """Calculate the size (in bytes) a buffer needs to hold an image with the current
        settings."""
        width, height, _, _ = self._get_sizes()
        return (width * height * self._data_depth()) // 16 * 2

    def _set_binning(self, hbin, vbin):
        self._cam.SetBinning(hbin, vbin)

    def start_capture(self, **kwds):
        self._handle_kwds(kwds)

        self._set_binning(kwds['vbin'], kwds['hbin'])
        self._set_ROI(kwds['left'], kwds['top'], kwds['right'], kwds['bot'])
        self._set_delay_exposure_time(delay='0s', exposure=kwds['exposure_time'])
        self._cam.ArmCamera()
        self._allocate_buffers(kwds['n_frames'])
        self._cam.ArmCamera()

        if 'trig' in kwds:
            self.set_trigger_mode(kwds['trig'], kwds.get('rising', True))

        # Prepare CameraLink interface
        width, height, _, _ = self._get_sizes()
        self._cam.SetTransferParametersAuto()
        self._cam.ArmCamera()
        self._cam.CamLinkSetImageParameters(width, height)

        # Add buffers to the queue
        for buf in self.buffers:
            self._push_on_queue(buf)

        self._cam.SetRecordingState(1)

        if self._trig_mode == self.TriggerMode.software:
            self._cam.ForceTrigger()

    def cancel_capture(self):
        """Cancel a capture sequence, cleaning up and stopping the camera"""
        self._cam.SetRecordingState(0)
        self._clear_queue()

    @check_units(timeout='?ms')
    def get_captured_image(self, timeout='1s', copy=True, wait_for_all=True, **kwds):
        self._handle_kwds(kwds)
        width, height, _, _ = self._get_sizes()
        frame_size = self._frame_size()
        image_arrs = []

        if not self.queue:
            raise Error("No capture initiated. You must first call start_capture()")

        start_time = clock() * u.s
        # Can't loop directly through queue since wait_for_frame modifies it
        while self.queue:
            buf = self.queue[0]
            if timeout is None:
                frame_ready = self.wait_for_frame(timeout=None)
            else:
                elapsed_time = clock() * u.s - start_time
                frame_ready = self.wait_for_frame(timeout - elapsed_time)

            if not frame_ready:
                if wait_for_all or not image_arrs:
                    self._partial_sequence.extend(image_arrs)  # Save for later
                    raise TimeoutError
                else:
                    break

            if copy:
                image_buf = memoryview(ffi.buffer(buf.address, frame_size)[:])
            else:
                image_buf = memoryview(ffi.buffer(buf.address, frame_size))

            # Convert to array (currently assumes mono16)
            array = np.frombuffer(image_buf, np.uint16)
            array = array.reshape((height, width))

            if kwds['fix_hotpixels']:
                array = self._correct_hot_pixels(array)

            # Handle soft ROI
            left, top = self._roi_trim_left, self._roi_trim_top
            array = array[top:top + self._soft_height, left:left + self._soft_width]

            image_arrs.append(array)
        image_arrs = self._partial_sequence + image_arrs

        if not self.queue:
            # Stop recording and clean up queue
            self._cam.SetRecordingState(0)
            self._clear_queue()
            self._partial_sequence = []

        if len(image_arrs) == 1:
            return image_arrs[0]
        else:
            return tuple(image_arrs)

    def grab_image(self, timeout='1s', copy=True, **kwds):
        self.start_capture(**kwds)
        return self.get_captured_image(timeout=timeout, copy=copy, **kwds)

    @check_units(framerate='Hz')
    def start_live_video(self, framerate='10Hz', **kwds):
        self._handle_kwds(kwds)

        self.set_trigger_mode(self.TriggerMode.auto)
        self._set_binning(kwds['vbin'], kwds['hbin'])
        self._set_ROI(kwds['left'], kwds['top'], kwds['right'], kwds['bot'])
        self._cam.ArmCamera()

        # Prepare CameraLink interface
        width, height, _, _ = self._get_sizes()
        self._cam.SetTransferParametersAuto()
        self._set_framerate(framerate, kwds['exposure_time'])
        self._cam.ArmCamera()
        self._cam.CamLinkSetImageParameters(width, height)

        self.shutter = 'continuous'
        if self._frame_size() != self._buf_size or len(self.buffers) < 2:
            self._allocate_buffers(nbufs=2)
        self._cam.ArmCamera()

        # Add all the buffers to the queue
        for buf in self.buffers:
            self._push_on_queue(buf)

        self._cam.SetRecordingState(1)
        self._cam.ForceTrigger()

    def stop_live_video(self):
        self._cam.SetRecordingState(0)
        self._clear_queue()
        self._free_buffers()
        self.shutter = None

    @unit_mag(timeout='?ms')
    def wait_for_frame(self, timeout=None):
        if not self.queue:
            raise Exception("No queued buffers!")

        timeout = winlib.INFINITE if timeout is None else max(0, timeout)

        # Wait for the next buffer event to fire
        buf = self.queue[0]
        ret = winlib.WaitForSingleObject(buf.event, int(timeout))
        if ret == winlib.WAIT_OBJECT_0:
            dll_status, drv_status = self._cam.GetBufferStatus(buf.num)
            if drv_status != 0:
                raise Exception(get_error_text(drv_status))
            winlib.ResetEvent(buf.event)
        elif ret == winlib.WAIT_TIMEOUT:
            return False
        else:
            raise Error("Failed to grab image")

        self.last_buffer = self.queue.pop(0)  # Pop and save only on success

        if self.shutter == 'continuous':
            self._push_on_queue(buf)  # Add buf back to the end of the queue

        return True

    def latest_frame(self, copy=True):
        buf_info = self.last_buffer
        if copy:
            buf = memoryview(ffi.buffer(buf_info.address, self._frame_size())[:])
        else:
            buf = memoryview(ffi.buffer(buf_info.address, self._frame_size()))

        width, height, _, _ = self._get_sizes()
        array = np.frombuffer(buf, np.uint16)
        array = array.reshape((height, width))

        # Handle soft ROI
        left, top = self._roi_trim_left, self._roi_trim_top
        return array[top:top + self._soft_height, left:left + self._soft_width]

    def _color_mode(self):
        desc = self._get_camera_description()
        if desc.wPatternTypeDESC & 0x01:  # All odd-numbered sensors are color
            return 'RGB32'
        else:
            return 'mono' + str(self.bit_depth)

    width = property(lambda self: self._soft_width)
    height = property(lambda self: self._soft_height)
    max_width = property(lambda self: self._get_sizes()[2])
    max_height = property(lambda self: self._get_sizes()[3])

    #: Color mode string ('mono16', 'RGB32', etc.)
    color_mode = property(lambda self: self._color_mode())

    #: Number of bits per pixel in the on-PC image
    bit_depth = property(lambda self: self._data_depth())

    #: Framerate in live mode
    framerate = property(lambda self: self._framerate())


def list_instruments():
    openStruct_p = ffi.new('PCO_OpenStruct *')
    openStruct = openStruct_p[0]
    openStruct.wSize = ffi.sizeof('PCO_OpenStruct')
    openStruct.wCameraNumber = 0

    paramsets = []
    prev_handle = None

    while True:
        openStruct.wInterfaceType = 0xFFFF  # Try all interfaces
        openStruct.wCameraNumAtInterface = 0
        openStruct.wOpenFlags[0] = 0

        try:
            log.info("Opening PCO camera")
            hCam, _ = NicePCO.OpenCameraEx(ffi.NULL, openStruct_p)  # This is reallllyyyy sloowwwww
        except Error as e:
            if e.code == 0x800A300D:
                return []  # No cameras attached/turned on
            raise

        _cam = NicePCO.Camera(hCam)

        if openStruct.wInterfaceType == 0xFFFF or hCam == prev_handle:
            # OpenCameraEx doesn't seem to return error upon not finding a camera, so if it didn't
            # set wInterfaceType, or the handle is the same as the previous handle, we assume it
            # found no camera
            _cam.CloseCamera()
            break
        else:
            paramset = ParamSet(PCO_Camera, number=openStruct.wCameraNumber,
                                interface=openStruct.wInterfaceType)
            paramsets.append(paramset)
            _cam.CloseCamera()
            prev_handle = hCam

        openStruct.wCameraNumber += 1
    return paramsets


def _instrument(paramset):
    # Because opening devices is so slow, we override the default implementation which
    # calls list_instruments. This instead just tries to open the camera
    return PCO_Camera._create(paramset)  # FIXME
