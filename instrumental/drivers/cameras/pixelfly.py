# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz
"""
Driver for PCO Pixelfly cameras.
"""

import atexit
import os.path
import numpy as np
from cffi import FFI
import win32event

from . import _err
from ._pixelfly import macros
from . import Camera
from .. import InstrumentTypeError, _ParamDict
from ... import Q_

__all__ = ['Pixelfly']


ffi = FFI()
with open(os.path.join(os.path.dirname(__file__), '_pixelfly', 'Pccam_clean.h')) as f:
    ffi.cdef(f.read())
lib = ffi.dlopen('pf_cam')  # Developed using version 2.1.0.29 of pf_cam.dll


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
            pbuf = _err.ffi.new('char[]', 1024)
            _err.lib.PCO_GetErrorText(_err.ffi.cast('unsigned int', ret_code), pbuf, len(pbuf))
            err_message = _err.ffi.string(pbuf)
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
    open_cameras = []

    def __init__(self, board_num=0):
        hdriver_p = ffi.new('HANDLE *', ffi.NULL)
        px.INITBOARD(board_num, hdriver_p)
        self._hdriver_p = hdriver_p
        self.hdriver = hdriver_p[0]
        self.cam_started = False
        self.mode_set = False
        self.mem_set_up = False

        # For saving
        self._param_dict = _ParamDict("<Pixelfly '{}'>".format(board_num))
        self._param_dict.module = 'cameras.pixelfly'
        self._param_dict['module'] = 'cameras.pixelfly'
        self._param_dict['pixelfly_board_num'] = board_num

        self.bufsizes = []
        self.bufnums = []
        self.bufptrs = []
        self.buf_events = []
        self.nbufs = 0
        self.buf_i = 0

        self.set_mode()
        self.open_cameras.append(self)

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
        if self.cam_started:
            px.STOP_CAMERA(self.hdriver)

        px.REMOVE_ALL_BUFFERS_FROM_LIST(self.hdriver)
        for bufnum in self.bufnums:
            px.FREE_BUFFER(self.hdriver, bufnum)
        self.bufsizes, self.bufnums, self.bufptrs = [], [], []
        self.nbufs = 0

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

        self.shutter = shutter

        # Camera must be stopped before SETMODE is called
        if self.cam_started:
            px.STOP_CAMERA(self.hdriver)

        px.SETMODE(self.hdriver, mode, 0, exptime, hbin_val, vbin_val,
                   gain_val, 0, bit_pix, 0)

        self._load_sizes()
        self.bytes_per_line = self.width*2
        self._allocate_buffers()
        self.color_mode = 'mono16'

    def start_live_video(self, framerate=10):
        self.framerate = 100 if framerate is None else framerate
        self.set_mode('video')
        self._trigger()

    def stop_live_video(self):
        self.set_mode()

    def wait_for_frame(self, timeout=1000):
        ptr = ffi.new('int[4]')
        buf_i = self.buf_i  # Save before we trigger
        ret = win32event.WaitForSingleObject(int(self.buf_events[buf_i]), timeout)

        if ret != win32event.WAIT_OBJECT_0:
            return False  # Object is not signaled

        win32event.ResetEvent(int(self.buf_events[buf_i]))
        px.PCC_RESETEVENT(self.hdriver, buf_i)
        px.GETBUFFER_STATUS(self.hdriver, self.bufnums[buf_i], 0, ptr, ffi.sizeof('DWORD')*1)

        if px.PCC_BUF_STAT_ERROR(ptr):
            uptr = ffi.cast('DWORD *', ptr)
            raise Exception("Buffer error 0x{:08X} 0x{:08X} 0x{:08X} 0x{:08X}".format(
                                uptr[0], uptr[1], uptr[2], uptr[3]))

        if self.shutter == 'video':
            px.ADD_BUFFER_TO_LIST(self.hdriver, self.bufnums[self.buf_i], self._frame_size(), 0, 0)
            self.buf_i = (self.buf_i + 1) % self.nbufs

        return True

    def _frame_size(self):
        return self.width * self.height * (self.bit_depth/8 + 1)

    def _allocate_buffers(self, nbufs=None):
        if nbufs is None:
            if self.nbufs > 1:
                nbufs = self.nbufs
            elif self.shutter == 'video':
                nbufs = 2
            else:
                nbufs = 1

        frame_size = self._frame_size()
        bufnr_p = ffi.new('int *')

        # Remove and free all existing buffers
        px.REMOVE_ALL_BUFFERS_FROM_LIST(self.hdriver)
        for bufnum in self.bufnums:
            px.FREE_BUFFER(self.hdriver, bufnum)
        self.bufnums = []
        self.bufsizes = []
        self.buf_events = []
        self.bufptrs = []

        # Create new buffers
        for i in range(nbufs):
            adr = ffi.new('void **')
            bufnr_p[0] = -1  # Allocate new buffer
            event_p = ffi.new('HANDLE *', ffi.NULL)

            px.ALLOCATE_BUFFER_EX(self.hdriver, bufnr_p, frame_size, event_p, adr)

            self.bufnums.append(bufnr_p[0])
            self.bufsizes.append(frame_size)
            self.buf_events.append(ffi.cast('unsigned int', event_p[0]))
            self.bufptrs.append(ffi.cast('void *', adr[0]))
        self.nbufs = nbufs

        px.START_CAMERA(self.hdriver)
        self.cam_started = True

        self.mem_set_up = True

    def _trigger(self):
        frame_size = self._frame_size()

        if self.shutter == 'video':
            for i in range(self.nbufs):
                px.ADD_BUFFER_TO_LIST(self.hdriver, self.bufnums[i],
                                      frame_size, 0, 0)
            self.buf_i = 0
        else:
            px.ADD_BUFFER_TO_LIST(self.hdriver, self.bufnums[self.buf_i],
                                  frame_size, 0, 0)
            self.buf_i = (self.buf_i + 1) % self.nbufs

        px.TRIGGER_CAMERA(self.hdriver)

    def _buffer_status(self):
        ptr = ffi.new('DWORD[23]')
        px.GETBUFFER_STATUS(self.hdriver, self.bufnums[self.buf_i], 0,
                            ffi.cast('int *', ptr), ffi.sizeof('DWORD')*23)
        return ptr

    def _board_param(self):
        ptr = ffi.new('DWORD[21]')
        px.GETBOARDPAR(self.hdriver, ptr, ffi.sizeof('DWORD'))
        return ptr

    def image_buffer(self):
        buf_i = (self.buf_i - 1) % self.nbufs
        return buffer(ffi.buffer(self.bufptrs[buf_i], self._frame_size())[:])

    def freeze_frame(self):
        self.grab_frame()

    def grab_frame(self):
        """ Trigger a capture sequence and return a buffer to the image data.

        To get the images in ndarray form instead, use ``grab_ndarray``.

        The type of capture sequence performed and its parameters can be
        changed with ``set_mode``.

        Returns
        -------
        cffi.buffer
            A cffi buffer that contains the bytes of the image(s).
        """
        ptr = ffi.new('int[4]')
        buf_i = self.buf_i  # Save before we trigger
        self._trigger()

        win32event.WaitForSingleObject(int(self.buf_events[buf_i]), 1000)
        win32event.ResetEvent(int(self.buf_events[buf_i]))
        px.GETBUFFER_STATUS(self.hdriver, self.bufnums[buf_i], 0, ptr, ffi.sizeof('int')*4)

        if px.PCC_BUF_STAT_ERROR(ptr):
            uptr = ffi.cast('DWORD *', ptr)
            raise Exception("Buffer error 0x{:08X} 0x{:08X} 0x{:08X} 0x{:08X}".format(
                                uptr[0], uptr[1], uptr[2], uptr[3]))

        return buffer(ffi.buffer(self.bufptrs[buf_i], self._frame_size())[:])

    def grab_ndarray(self):
        """ Trigger a capture sequence and return the image(s) as ndarray(s).

        To get a buffer of raw bytes instead, use ``grab_frame``.

        The type of capture sequence performed and its parameters can be
        changed with ``set_mode``.

        Returns
        -------
        numpy.ndarray or tuple of numpy.ndarrays
            The grayscale image data in ndarray form. Uses a dtype of np.uint8
            for 8-bit data and np.uint16 for 12-bit data.
        """
        dtype = np.uint8 if self.bit_depth <= 8 else np.uint16
        buf = self.grab_frame()

        if self.height/self.ccd_height == 1:
            arr = np.frombuffer(buf, dtype)
            return arr.reshape((self.height, self.width))
        else:
            # act_h is combined height of both frames
            px_per_frame = self.width*self.height/2
            byte_per_px = self.bit_depth/8 + 1
            arr1 = np.frombuffer(buf, dtype, px_per_frame, 0)
            arr2 = np.frombuffer(buf, dtype, px_per_frame, px_per_frame*byte_per_px)
            return (arr1.reshape((self.height/2, self.width)),
                    arr2.reshape((self.height/2, self.width)))

    def _load_sizes(self):
        ccdx_p = ffi.new('int *')
        ccdy_p = ffi.new('int *')
        actualx_p = ffi.new('int *')
        actualy_p = ffi.new('int *')
        bit_pix_p = ffi.new('int *')
        px.GETSIZES(self.hdriver, ccdx_p, ccdy_p, actualx_p, actualy_p, bit_pix_p)
        self._ccd_width = ccdx_p[0]
        self._ccd_height = ccdy_p[0]
        self._width = actualx_p[0]
        self._height = actualy_p[0]
        self._bit_depth = bit_pix_p[0]

    def temperature(self):
        """ The temperature of the CCD. """
        temp_p = ffi.new('int *')
        px.READTEMPERATURE(self.hdriver, temp_p)
        return Q_(temp_p[0], 'degC')

    width = property(lambda self: self._width)
    height = property(lambda self: self._height)
    bit_depth = property(lambda self: self._bit_depth)
    ccd_width = property(lambda self: self._ccd_width)
    ccd_height = property(lambda self: self._ccd_height)


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
    for cam in Pixelfly.open_cameras:
        try:
            cam.close()
        except:
            pass


def close_all():
    hdriver_p = ffi.new('HANDLE *', ffi.NULL)
    px.INITBOARD(0, hdriver_p)
    px.STOP_CAMERA(hdriver_p[0])
    px.CLOSEBOARD(hdriver_p)
