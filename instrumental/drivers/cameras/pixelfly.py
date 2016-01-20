# -*- coding: utf-8 -*-
# Copyright 2015-2016 Nate Bogdanowicz
"""
Driver for PCO Pixelfly cameras.
"""

import atexit
import os.path
import numpy as np
from cffi import FFI
import win32event

from ._pixelfly import errortext
from ._pixelfly import macros
from . import Camera
from .. import InstrumentTypeError, _ParamDict
from ..util import check_units
from ...errors import Error, TimeoutError
from ... import Q_

__all__ = ['Pixelfly']


ffi = FFI()
with open(os.path.join(os.path.dirname(__file__), '_pixelfly', 'Pccam_clean.h')) as f:
    ffi.cdef(f.read())
lib = ffi.dlopen('pf_cam.dll')  # Developed using version 2.1.0.29 of pf_cam.dll


# Here we create a proxy for 'lib' that includes some nicer features like
# automatic error handling, includes enums, and excludes pl_ from function
# names
class PixelflyLib(object):
    pass
px = PixelflyLib()


px_funcs = [
    'INITBOARD',
    'CLOSEBOARD',
    'GETBOARDPAR',
    'GETBOARDVAL',
    'SETMODE',
    'GETMODE',
    'WRRDORION',
    'SET_EXPOSURE',
    'TRIGGER_CAMERA',
    'START_CAMERA',
    'STOP_CAMERA',
    'GETSIZES',
    'READTEMPERATURE',
    'READVERSION',
    'GETBUFFER_STATUS',
    'ADD_BUFFER_TO_LIST',
    'REMOVE_BUFFER_FROM_LIST',
    'REMOVE_ALL_BUFFERS_FROM_LIST',
    'ALLOCATE_BUFFER',
    'ALLOCATE_BUFFER_EX',
    'FREE_BUFFER',
    'SETBUFFER_EVENT',
    'MAP_BUFFER',
    'UNMAP_BUFFER',
    'SETORIONINT',
    'GETORIONINT',
    'READEEPROM',
    'WRITEEEPROM',
    'SETTIMEOUTS',
    'SETDRIVER_EVENT',
    'READ_TEMP',
    'SET_NOMINAL_PELTIER_TEMP',
    'GET_NOMINAL_PELTIER_TEMP',
    'SET_STANDBY_MODE',
    'GET_STANDBY_MODE',
    'PCC_MEMCPY',
    'PCC_GET_VERSION',
    'PCC_WAITFORBUFFER',
    'PCC_RESETEVENT'
]

# Include enums from CFFI library version of headers
# for some reason, enums aren't available until after first dir()...
dir(lib)
for name in dir(lib):
    if not name.startswith('__'):
        setattr(px, name, getattr(lib, name))

ERR_CODE_MAP = {
    -1: 'Initialization failed; no camera connected',
    -2: 'Timeout',
    -3: 'Function called with wrong parameter',
    -4: 'Cannot locate PCI card or card driver',
    -5: 'Wrong operating system',
    -6: 'No driver or wrong driver is installed',
    -7: 'IO function failed',
    -8: 'Reserved',
    -9: 'Invalid camera mode',
    -10: 'Reserved',
    -11: 'Device is held by another process',
    -12: 'Error in reading or writing data to board',
    -13: 'Wrong driver function',
    -14: 'Reserved'
}

# Include selected macros from headers
for name in dir(macros):
    if not name.startswith('__'):
        setattr(px, name, getattr(macros, name))


def err_wrap(func):
    def err_wrapped(*args):
        ret_code = func(*args)
        if ret_code != 0:
            pbuf = errortext.ffi.new('char[]', 1024)
            errortext.lib.PCO_GetErrorText(errortext.ffi.cast('unsigned int', ret_code), pbuf,
                                           len(pbuf))
            err_message = errortext.ffi.string(pbuf)
            e = Exception('({}) {}'.format(ret_code, err_message))
            e.err_code = ret_code
            raise e
    err_wrapped.__name__ = str(func)
    return err_wrapped


# Include (and wrap) functions from CFFI library
for func_name in px_funcs:
    func = getattr(lib, func_name)
    setattr(px, func_name, err_wrap(func))


class Pixelfly(Camera):
    _open_cameras = []

    def __init__(self, board_num=0):
        hdriver_p = ffi.new('HANDLE *', ffi.NULL)
        px.INITBOARD(board_num, hdriver_p)
        self._hdriver_p = hdriver_p
        self._hcam = hdriver_p[0]
        self._cam_started = False
        self._mode_set = False
        self._mem_set_up = False

        # For saving
        self._param_dict = _ParamDict("<Pixelfly '{}'>".format(board_num))
        self._param_dict.module = 'cameras.pixelfly'
        self._param_dict['module'] = 'cameras.pixelfly'
        self._param_dict['pixelfly_board_num'] = board_num

        self._bufsizes = []
        self._bufnums = []
        self._bufptrs = []
        self._buf_events = []
        self._nbufs = 0
        self._buf_i = 0

        self.set_mode()
        self._open_cameras.append(self)

    @staticmethod
    def _list_boards():
        hdriver_p = ffi.new('HANDLE *', ffi.NULL)
        board_nums = []

        for board_num in range(4):
            try:
                px.INITBOARD(board_num, hdriver_p)
            except Exception:
                pass
            else:
                px.CLOSEBOARD(hdriver_p)
                board_nums.append(board_num)
        return board_nums

    def close(self):
        """ Clean up memory and close the camera."""
        if self._cam_started:
            px.STOP_CAMERA(self._hcam)

        px.REMOVE_ALL_BUFFERS_FROM_LIST(self._hcam)
        for bufnum in self._bufnums:
            px.FREE_BUFFER(self._hcam, bufnum)
        self._bufsizes, self._bufnums, self._bufptrs = [], [], []
        self._nbufs = 0

        px.CLOSEBOARD(self._hdriver_p)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def set_mode(self, shutter='single', trig='software', exposure='10ms',
                 hbin=1, vbin=1, gain='low', depth=12):
        """ Set the mode of the camera.

        Parameters
        ----------
        shutter : str
            One of 'single', 'double', or 'video'.
        trig : str
            One of 'software' or 'hardware'.
        exposure : Quantity or str
            Exposure time. Up to 65.6 ms with microsecond resolution.
        hbin : int
            Horizontal binning factor. Either 1 or 2.
        vbin : int
            Vertical binning factor. Either 1 or 2.
        gain : str
            Gain of camera. Either 'low' or 'high'.
        depth : int
            Bit depth of each pixel. Either 8 or 12.
        """
        # Normalize all the parameters
        shutter_map = {'single': 0x10, 'double': 0x20, 'video': 0x30}
        mode = shutter_map[shutter] + (1 if trig == 'software' else 0)
        exp_units = 'ms' if shutter == 'video' else 'us'
        exptime = int(Q_(exposure).to(exp_units).magnitude)

        hbin_val = 0 if hbin == 1 else 1
        vbin_val = 0 if vbin == 1 else 1
        gain_val = 0 if gain == 'low' else 1
        bit_pix = 12 if depth == 12 else 8

        self._shutter = shutter

        # Camera must be stopped before SETMODE is called
        if self._cam_started:
            px.STOP_CAMERA(self._hcam)

        px.SETMODE(self._hcam, mode, 0, exptime, hbin_val, vbin_val,
                   gain_val, 0, bit_pix, 0)

        self._load_sizes()
        self._allocate_buffers()
        self.color_mode = 'mono16'

    def start_live_video(self, **kwds):
        self.set_mode('video')
        self._trigger()

    def stop_live_video(self):
        self.set_mode()

    @check_units(timeout='?ms')
    def wait_for_frame(self, timeout=None):
        """wait_for_frame(self, timeout=None')"""
        ptr = ffi.new('int[4]')
        buf_i = (self._buf_i - 1) % self._nbufs  # Most recently triggered buffer
        ret = win32event.WaitForSingleObject(int(self._buf_events[buf_i]), int(timeout.m_as('ms')))

        if ret != win32event.WAIT_OBJECT_0:
            return False  # Object is not signaled

        win32event.ResetEvent(int(self._buf_events[buf_i]))
        px.PCC_RESETEVENT(self._hcam, buf_i)
        px.GETBUFFER_STATUS(self._hcam, self._bufnums[buf_i], 0, ptr, ffi.sizeof('DWORD')*1)

        if px.PCC_BUF_STAT_ERROR(ptr):
            uptr = ffi.cast('DWORD *', ptr)
            raise Exception("Buffer error 0x{:08X} 0x{:08X} 0x{:08X} 0x{:08X}".format(
                                uptr[0], uptr[1], uptr[2], uptr[3]))

        if self._shutter == 'video':
            px.ADD_BUFFER_TO_LIST(self._hcam, self._bufnums[self._buf_i], self._frame_size(), 0, 0)
            self._buf_i = (self._buf_i + 1) % self._nbufs

        return True

    def _frame_size(self):
        return self.width * self.height * (self.bit_depth/8 + 1)

    def _allocate_buffers(self, nbufs=None):
        if nbufs is None:
            if self._nbufs > 1:
                nbufs = self._nbufs
            elif self._shutter == 'video':
                nbufs = 2
            else:
                nbufs = 1

        frame_size = self._frame_size()
        bufnr_p = ffi.new('int *')

        # Remove and free all existing buffers
        px.REMOVE_ALL_BUFFERS_FROM_LIST(self._hcam)
        for bufnum in self._bufnums:
            px.FREE_BUFFER(self._hcam, bufnum)
        self._bufnums = []
        self._bufsizes = []
        self._buf_events = []
        self._bufptrs = []

        # Create new buffers
        for i in range(nbufs):
            adr = ffi.new('void **')
            bufnr_p[0] = -1  # Allocate new buffer
            event_p = ffi.new('HANDLE *', ffi.NULL)

            px.ALLOCATE_BUFFER_EX(self._hcam, bufnr_p, frame_size, event_p, adr)

            self._bufnums.append(bufnr_p[0])
            self._bufsizes.append(frame_size)
            self._buf_events.append(ffi.cast('unsigned int', event_p[0]))
            self._bufptrs.append(ffi.cast('void *', adr[0]))
        self._nbufs = nbufs

        px.START_CAMERA(self._hcam)
        self._cam_started = True

        self._mem_set_up = True

    def _trigger(self):
        frame_size = self._frame_size()

        if self._shutter == 'video':
            for i in range(self._nbufs):
                px.ADD_BUFFER_TO_LIST(self._hcam, self._bufnums[i],
                                      frame_size, 0, 0)
            self._buf_i = 0
        else:
            px.ADD_BUFFER_TO_LIST(self._hcam, self._bufnums[self._buf_i],
                                  frame_size, 0, 0)
            self._buf_i = (self._buf_i + 1) % self._nbufs

        px.TRIGGER_CAMERA(self._hcam)

    def _buffer_status(self):
        ptr = ffi.new('DWORD[23]')
        px.GETBUFFER_STATUS(self._hcam, self._bufnums[self._buf_i], 0,
                            ffi.cast('int *', ptr), ffi.sizeof('DWORD')*23)
        return ptr

    def _board_param(self):
        ptr = ffi.new('DWORD[21]')
        px.GETBOARDPAR(self._hcam, ptr, ffi.sizeof('DWORD'))
        return ptr

    def latest_frame(self, copy=True):
        buf_i = (self._buf_i - 1) % self._nbufs
        if copy:
            buf = buffer(ffi.buffer(self._bufptrs[buf_i], self._frame_size())[:])
        else:
            buf = buffer(ffi.buffer(self._bufptrs[buf_i], self._frame_size()))

        return self._array_from_buffer(buf)

    def start_capture(self, **kwds):
        self._handle_kwds(kwds)

        if kwds['n_frames'] > 1:
            raise Error("Pixelfly camera does not support multi-image capture sequences")

        self.set_mode(exposure=kwds['exposure_time'], hbin=kwds['hbin'], vbin=kwds['vbin'])
        self._trigger()

    def get_captured_image(self, timeout='1s', copy=True, **kwds):
        self._handle_kwds(kwds)  # Should get rid of this duplication somehow...

        # We can use wait_for_frame since the driver (currently) only supports capture sequences
        # that use one buffer at a time (double shutter mode uses one double-large buffer)
        ready = self.wait_for_frame(timeout=timeout)
        if not ready:
            raise TimeoutError("Image not ready")

        image = self.latest_frame(copy=copy)
        if kwds['fix_hotpixels']:
            image = self._correct_hot_pixels(image)  # Makes a copy on success

        return image

    def _array_from_buffer(self, buf):
        dtype = np.uint8 if self.bit_depth <= 8 else np.uint16
        if self._shutter != 'double':
            arr = np.frombuffer(buf, dtype)
            return arr.reshape((self.height, self.width))
        else:
            px_per_frame = self.width*self.height
            byte_per_px = self.bit_depth/8 + 1
            arr1 = np.frombuffer(buf, dtype, px_per_frame, 0)
            arr2 = np.frombuffer(buf, dtype, px_per_frame, px_per_frame*byte_per_px)
            return (arr1.reshape((self.height, self.width)),
                    arr2.reshape((self.height, self.width)))

    def grab_image(self, timeout='1s', copy=True, **kwds):
        self.start_capture(**kwds)
        return self.get_captured_image(timeout=timeout, copy=copy, **kwds)

    def _load_sizes(self):
        ccdx_p = ffi.new('int *')
        ccdy_p = ffi.new('int *')
        actualx_p = ffi.new('int *')
        actualy_p = ffi.new('int *')
        bit_pix_p = ffi.new('int *')
        px.GETSIZES(self._hcam, ccdx_p, ccdy_p, actualx_p, actualy_p, bit_pix_p)
        self._max_width = ccdx_p[0]
        self._max_height = ccdy_p[0]
        self._width = actualx_p[0]
        self._height = actualy_p[0]
        self._bit_depth = bit_pix_p[0]

        if self._shutter == 'double':
            self._height = self._height / 2  # Give the height of *each* image individually

    @property
    def temperature(self):
        """ The temperature of the CCD. """
        temp_p = ffi.new('int *')
        px.READTEMPERATURE(self._hcam, temp_p)
        return Q_(temp_p[0], 'degC')

    width = property(lambda self: self._width)
    height = property(lambda self: self._height)
    max_width = property(lambda self: self._max_width)
    max_height = property(lambda self: self._max_height)
    bit_depth = property(lambda self: self._bit_depth)


def list_instruments():
    board_nums = Pixelfly._list_boards()
    cams = []

    for board_num in board_nums:
        params = _ParamDict("<Pixelfly '{}'>".format(board_num))
        params.module = 'cameras.pixelfly'
        params['pixelfly_board_num'] = board_num
        cams.append(params)
    return cams


def _instrument(params):
    if 'pixelfly_board_num' in params:
        cam = Pixelfly(params['pixelfly_board_num'])
    elif params.module == 'cameras.pixelfly':
        cam = Pixelfly()
    else:
        raise InstrumentTypeError()
    return cam


@atexit.register
def _cleanup():
    for cam in Pixelfly._open_cameras:
        try:
            cam.close()
        except:
            pass


def close_all():
    hdriver_p = ffi.new('HANDLE *', ffi.NULL)
    px.INITBOARD(0, hdriver_p)
    px.STOP_CAMERA(hdriver_p[0])
    px.CLOSEBOARD(hdriver_p)
