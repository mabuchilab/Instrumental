# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz
"""
Driver for PCO Pixelfly cameras.
"""

import os.path
import numpy as np
from cffi import FFI
from ._pixelfly import macros
from . import Camera
from .. import InstrumentTypeError, _ParamDict
from ... import Q_

__all__ = ['Pixelfly']


ffi = FFI()
with open(os.path.join(os.path.dirname(__file__), '_pixelfly', 'Pccam_clean.h')) as f:
    ffi.cdef(f.read())
lib = ffi.dlopen('pccam')


# Here we create a proxy for 'lib' that includes some nicer features like
# automatic error handling, includes enums, and excludes pl_ from function
# names
class PixelflyLib(object):
    pass
px = PixelflyLib()

px_funcs = [
    'INITBOARD',
    'INITBOARDP',
    'CLOSEBOARD',
    'RESETBOARD',
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
    'GETBUFFERVAL',
    'ADD_BUFFER_TO_LIST',
    'ADD_PHYS_BUFFER_TO_LIST',
    'REMOVE_BUFFER_FROM_LIST',
    'ALLOCATE_BUFFER',
    'FREE_BUFFER',
    'SETBUFFER_EVENT',
    'MAP_BUFFER',
    'MAP_BUFFER_EX',
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
            err_message = ERR_CODE_MAP.get(ret_code, '')
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
    def __init__(self, board_num=0):
        hdriver_p = ffi.new('HANDLE *', ffi.NULL)
        px.INITBOARD(board_num, hdriver_p)
        self._hdriver_p = hdriver_p
        self.hdriver = hdriver_p[0]
        self.cam_started = False
        self.mode_set = False
        self.mem_set_up = False
        self.bufnr = -1  # Allocate a buffer the first time around

        self.set_mode()
        self._allocate_buffer()

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
        if self.mem_set_up:
            px.UNMAP_BUFFER(self.hdriver, self.bufnr)
            px.FREE_BUFFER(self.hdriver, self.bufnr)
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
        exptime = int(Q_(exposure).to('us').magnitude)
        hbin_val = 0 if hbin == 1 else 1
        vbin_val = 0 if vbin == 1 else 1
        gain_val = 0 if gain == 'low' else 1
        bit_pix = 12 if depth == 12 else 8

        # Camera must be stopped before SETMODE is called
        if self.cam_started:
            px.STOP_CAMERA(self.hdriver)

        px.SETMODE(self.hdriver, mode, 0, exptime, hbin_val, vbin_val,
                   gain_val, 0, bit_pix, 0)

        if self.mem_set_up:
            self._allocate_buffer()
        elif self.cam_started:
            # 'elif' b/c _allocate_buffer() starts the camera already
            px.START_CAMERA(self.hdriver)

    def _allocate_buffer(self):
        _, _, act_w, act_h, bit_pix = self._get_sizes()
        byte_per_pix = 1 if bit_pix == 8 else 2
        size_p = ffi.new('int *', act_w*act_h*byte_per_pix)
        bufnr_p = ffi.new('int *', self.bufnr)
        linadr = ffi.new('DWORD *')

        if self.mem_set_up:
            px.UNMAP_BUFFER(self.hdriver, self.bufnr)

        px.ALLOCATE_BUFFER(self.hdriver, bufnr_p, size_p)
        px.MAP_BUFFER(self.hdriver, bufnr_p[0], size_p[0], 0, linadr)
        px.START_CAMERA(self.hdriver)
        self.cam_started = True

        self.bufsize = size_p[0]
        self.bufnr = bufnr_p[0]
        self.buf_p = ffi.cast('void *', linadr[0])  # This is so stupid
        self.mem_set_up = True

    def _trigger(self):
        _, _, act_w, act_h, bit_pix = self._get_sizes()
        byte_per_pix = 1 if bit_pix == 8 else 2
        px.ADD_BUFFER_TO_LIST(self.hdriver, self.bufnr, act_w*act_h*byte_per_pix, 0, 0)
        px.TRIGGER_CAMERA(self.hdriver)

    def _buffer_status(self):
        ptr = ffi.new('DWORD[23]')
        px.GETBUFFER_STATUS(self.hdriver, self.bufnr, 0,
                            ffi.cast('int *', ptr), ffi.sizeof('DWORD')*23)
        return ptr

    def _board_param(self):
        ptr = ffi.new('DWORD[21]')
        px.GETBOARDPAR(self.hdriver, ptr, ffi.sizeof('DWORD'))
        return ptr

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
        ptr = ffi.new('int *')
        self._trigger()

        # Spin until memory transfer is done
        done = False
        while not done:
            px.GETBUFFER_STATUS(self.hdriver, self.bufnr, 0, ptr, ffi.sizeof('DWORD')*1)
            done = px.PCC_BUF_STAT_WRITE_DONE(ffi.cast('DWORD *', ptr))

        if px.PCC_BUF_STAT_ERROR(ptr):
            raise Exception("Buffer error {}".format(px.PCC_BUF_STAT_ERROR(ptr)))

        _, _, act_w, act_h, bit_pix = self._get_sizes()
        byte_per_pix = 1 if bit_pix == 8 else 2
        return ffi.buffer(self.buf_p, act_w*act_h*byte_per_pix)

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
        ccd_w, ccd_h, act_w, act_h, bit_pix = self._get_sizes()
        dtype = np.uint8 if bit_pix == 8 else np.uint16
        byte_per_pix = 1 if bit_pix == 8 else 2
        buf = self.grab_frame()

        if act_h/ccd_h == 1:
            arr = np.frombuffer(buf, dtype)
            return arr.reshape((act_h, act_w))
        else:
            # act_h is combined height of both frames
            pix_per_frame = act_w*act_h/2
            arr1 = np.frombuffer(buf, dtype, pix_per_frame, 0)
            arr2 = np.frombuffer(buf, dtype, pix_per_frame, pix_per_frame*byte_per_pix)
            return arr1.reshape((act_h/2, act_w)), arr2.reshape((act_h/2, act_w))

    def _get_sizes(self):
        ccdx_p = ffi.new('int *')
        ccdy_p = ffi.new('int *')
        actualx_p = ffi.new('int *')
        actualy_p = ffi.new('int *')
        bit_pix_p = ffi.new('int *')
        px.GETSIZES(self.hdriver, ccdx_p, ccdy_p, actualx_p, actualy_p, bit_pix_p)
        return ccdx_p[0], ccdy_p[0], actualx_p[0], actualy_p[0], bit_pix_p[0]

    def temperature(self):
        """ The temperature of the CCD. """
        temp_p = ffi.new('int *')
        px.READTEMPERATURE(self.hdriver, temp_p)
        return Q_(temp_p[0], 'degC')


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
