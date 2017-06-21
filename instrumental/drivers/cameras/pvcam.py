# -*- coding: utf-8 -*-
# Copyright 2015-2017 Nate Bogdanowicz
"""
Driver for Photometrics cameras.
"""

import time
import os.path
import numpy as np
from cffi import FFI
from ._pvcam import macros
from . import Camera
from .. import _ParamDict
from ..util import check_units
from ...errors import InstrumentTypeError, InstrumentNotFoundError
from ... import Q_, u

__all__ = ['PVCam']

ffi = FFI()
with open(os.path.join(os.path.dirname(__file__), '_pvcam', 'pvcam_clean.h')) as f:
    ffi.cdef(f.read())
lib = ffi.dlopen('Pvcam32')


# Here we create a proxy for 'lib' that includes some nicer features like
# automatic error handling, includes enums, and excludes pl_ from function
# names
class PLLib(object):
    pass
pv = PLLib()

pv_funcs = [
    'cam_check',
    'cam_close',
    'cam_deregister_callback',
    'cam_get_diags',
    'cam_get_name',
    'cam_get_total',
    'cam_open',
    'cam_register_callback',
    'ddi_get_ver',
    'pvcam_get_ver',
    'pvcam_init',
    'pvcam_uninit',
    'error_code',
    'error_message',
    'enum_str_length',
    'get_enum_param',
    'get_param',
    'pp_reset',
    'set_param',
    'exp_abort',
    'exp_check_cont_status',
    'exp_check_status',
    'exp_finish_seq',
    'exp_get_driver_buffer',
    'exp_get_latest_frame',
    'exp_get_oldest_frame',
    'exp_init_seq',
    'exp_setup_cont',
    'exp_setup_seq',
    'exp_start_cont',
    'exp_start_seq',
    'exp_stop_cont',
    'exp_uninit_seq',
    'exp_unlock_oldest_frame',
    'exp_unravel',
    'io_clear_script_control',
    'io_script_control',
    'buf_alloc',
    'buf_free',
    'buf_get_bits',
    'buf_get_exp_date',
    'buf_get_exp_time',
    'buf_get_exp_total',
    'buf_get_img_bin',
    'buf_get_img_handle',
    'buf_get_img_ofs',
    'buf_get_img_ptr',
    'buf_get_img_size',
    'buf_get_img_total',
    'buf_get_size',
    'buf_init',
    'buf_set_exp_date',
    'buf_uninit'
]

# Include macro-constants from headers
for name in dir(macros):
    if not name.startswith('__'):
        setattr(pv, name, getattr(macros, name))

# Include enums from CFFI library version of headers
# for some reason, enums aren't available until after first dir()...
dir(lib)
for name in dir(lib):
    if not name.startswith('__'):
        setattr(pv, name, getattr(lib, name))


def err_wrap(func):
    def err_wrapped(*args):
        success = func(*args)
        if not success:
            msg = ffi.new('char[{}]'.format(pv.ERROR_MSG_LEN))
            err_code = lib.pl_error_code()
            lib.pl_error_message(err_code, msg)
            e = Exception(ffi.string(msg))
            e.err_code = err_code
            raise e
    err_wrapped.__name__ = str(func)
    return err_wrapped

# Include (and wrap) functions from CFFI library
for func_name in pv_funcs:
    func = getattr(lib, 'pl_'+func_name)
    setattr(pv, func_name, err_wrap(func))


class PVCam(Camera):
    num_cams_open = 0

    def start_capture(self, **kwds):
        raise NotImplementedError

    @check_units(timeout='?ms')
    def get_captured_image(self, timeout='1s', copy=True):
        raise NotImplementedError

    def grab_image(self, timeout='1s', copy=True, **kwds):
        raise NotImplementedError

    def latest_frame(self, copy=True):
        raise NotImplementedError

    def __init__(self, name=''):
        cam_name = ffi.new('char[{}]'.format(pv.CAM_NAME_LEN), name)
        hcam_p = ffi.new('int16[1]')

        if PVCam.num_cams_open == 0:
            self._try_init()
            pv.buf_init()

        if not name:
            pv.cam_get_name(0, cam_name)

        pv.cam_open(cam_name, hcam_p, lib.OPEN_EXCLUSIVE)
        pv.exp_init_seq()

        self.hcam = hcam_p[0]
        self.seq_is_set_up = False
        self.cont_is_set_up = False
        PVCam.num_cams_open += 1

        self.bytes_per_line = self.width*2
        self.color_mode = 'mono16'

        # For saving
        self._param_dict = _ParamDict("<PVCam '{}'>".format(name))
        self._param_dict['module'] = 'cameras.pvcam'
        self._param_dict['pvcam_name'] = ffi.string(cam_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @classmethod
    def _total_cams(cls):
        """The total number of cameras on the system"""
        if cls.num_cams_open == 0:
            PVCam._try_init()
            pv.buf_init()

        total_cams_p = ffi.new('int16_ptr')
        pv.cam_get_total(total_cams_p)

        if cls.num_cams_open == 0:
            cls._try_uninit()
            pv.buf_uninit()
        return total_cams_p[0]

    @classmethod
    def _cam_names(cls):
        """A list of the names of all cameras on the system"""
        if cls.num_cams_open == 0:
            PVCam._try_init()
            pv.buf_init()
        cls.num_cams_open += 1  # Fool _total_cams() so we don't have to reinit

        total = PVCam._total_cams()
        cam_name = ffi.new('char[{}]'.format(pv.CAM_NAME_LEN))

        names = []
        for i in range(total):
            pv.cam_get_name(i, cam_name)
            names.append(ffi.string(cam_name))

        cls.num_cams_open -= 1
        if cls.num_cams_open == 0:
            cls._try_uninit()
            pv.buf_uninit()

        return names

    @staticmethod
    def _try_init():
        try:
            pv.pvcam_init()
        except Exception as e:
            if e.err_code != pv.C2_PVCAM_ALREADY_INITED:
                raise e

    @staticmethod
    def _try_uninit():
        try:
            pv.pvcam_uninit()
        except Exception as e:
            if e.err_code not in (pv.C0_PVCAM_NOT_INITED,
                                  pv.C2_PVCAM_NOT_INITED):
                raise e

    def close(self):
        if self.seq_is_set_up:
            self._unsetup_sequence()
        elif self.cont_is_set_up:
            self.stop_live_video()
            pv.exp_uninit_seq()
        pv.cam_close(self.hcam)

        PVCam.num_cams_open -= 1
        if PVCam.num_cams_open == 0:
            self._try_uninit()
            pv.buf_uninit()

    def start_live_video(self, **kwds):
        raise NotImplementedError

        exposure_ms = kwds['exposure_time'].m_as('ms')

        if self.seq_is_set_up:
            #self._unsetup_sequence()
            pass
        mode = pv.TIMED_MODE

        w, h = self.width, self.height
        region_p = ffi.new('rgn_type *', (0, w-1, 1, 0, h-1, 1))
        frame_size_p = ffi.new('uns32 *')

        n_exposures = 2  # Double buffering
        n_regions = 1
        pv.exp_setup_cont(self.hcam, n_regions, region_p, mode, exposure_ms,
                          frame_size_p, pv.CIRC_OVERWRITE)

        # frame_size_p[0] is the number of BYTES per frame
        buffer_size = frame_size_p[0]*n_exposures
        self.stream_buf = ffi.new('uns16[{}]'.format(buffer_size/ffi.sizeof('uns16')))
        self.cont_is_set_up = True
        self.nframes = n_exposures

        pv.exp_start_cont(self.hcam, self.stream_buf, buffer_size)

    def stop_live_video(self):
        pv.exp_stop_cont(self.hcam, pv.CCS_HALT)
        self.cont_is_set_up = False

    def image_buffer(self):
        frame_p = ffi.new('void **')
        pv.exp_get_latest_frame(self.hcam, frame_p)

        f_nbytes = self.width*self.height*2
        return buffer(ffi.buffer(frame_p[0], f_nbytes)[:])

    def image_array(self):
        return self.grab_ndarray(fresh_capture=False)

    @check_units(timeout='?ms')
    def wait_for_frame(self, timeout=None):
        raise NotImplementedError

        status_p = ffi.new('int16_ptr')
        byte_cnt_p = ffi.new('uns32_ptr')
        buffer_cnt_p = ffi.new('uns32_ptr')

        t = time.clock() * u.s
        if timeout is not None:
            tfinal = t + timeout

        status = pv.READOUT_NOT_ACTIVE
        while status != pv.READOUT_COMPLETE and status != pv.READOUT_FAILED and (timeout is None or
                                                                                 t <= tfinal):
            pv.exp_check_cont_status(self.hcam, status_p, byte_cnt_p, buffer_cnt_p)
            status = status_p[0]
            t = time.clock() * u.s

        if status == pv.READOUT_FAILED:
            raise Exception("Data collection error: {}".format(pv.error_code()))

        return status == pv.READOUT_COMPLETE

    def setup_sequence(self, exp_time='100ms', nframes=1, mode='timed', regions=None):
        """
        Parameters
        ----------
        exp_time : int
            The exposure time, in milliseconds
        nframes : int
            The number of frames to expose during the sequence.
        mode : str
            The exposure mode. One of 'timed', 'variable', 'trigger',
            'strobed', 'bulb', and 'flash'.
        """
        if self.seq_is_set_up:
            pv.exp_finish_seq(self.hcam, self.stream_buf, 0)

        mode_map = {
            'timed': pv.TIMED_MODE,
            'variable': pv.VARIABLE_TIMED_MODE,
            'trigger': pv.TRIGGER_FIRST_MODE,
            'strobed': pv.STROBED_MODE,
            'bulb': pv.BULB_MODE,
            'flash': pv.FLASH_MODE
        }
        mode = mode_map[mode]

        w, h = self.width, self.height

        # Build region list
        if regions is None:
            self.regions = [(0, w-1, 1, 0, h-1, 1)]
        else:
            self.regions = []
            for region in regions:
                try:
                    # Verify region has six items
                    self.regions.append(tuple(region[0:6]))
                except TypeError:
                    # The tuple isn't nested yet, so nest it
                    self.regions = [tuple(regions[0:6])]
                    break

        # Region sizes in pixels
        self.region_sizes = []
        for region in self.regions:
            x0, x1, xbin, y0, y1, ybin = region
            self.region_sizes.append((x1-x0+1)*(y1-y0+1)/(xbin*ybin))

        region_p = ffi.new('rgn_type[]', self.regions)
        size_p = ffi.new('uns32 *')
        self.region_p = region_p

        n_exposures = int(nframes)
        exp_time = Q_(exp_time).to('ms').magnitude
        pv.exp_setup_seq(self.hcam, n_exposures, len(self.regions), region_p,
                         mode, exp_time, size_p)

        # Create buffer
        hbuf_p = ffi.new('int16_ptr')
        pv.buf_alloc(hbuf_p, n_exposures, pv.PRECISION_UNS16,
                     len(self.regions), region_p)
        self.hbuf = hbuf_p[0]

        # size_p[0] is the number of BYTES in the pixel stream
        # Do we need to worry about page-locking this memory?
        self.stream_buf = ffi.new('uns16[{}]'.format(size_p[0]/2))
        self.seq_is_set_up = True
        self.nframes = nframes

    def _unsetup_sequence(self):
        pv.exp_finish_seq(self.hcam, self.stream_buf, 0)
        pv.exp_uninit_seq()

    def start_capture(self):
        pv.exp_start_seq(self.hcam, self.stream_buf)

    def abort_sequence(self):
        pv.exp_abort(self.hcam, pv.CCS_HALT)

    def grab_frame(self, fresh_capture=True, force_list=False, timeout=-1):
        status_p = ffi.new('int16_ptr')
        byte_cnt_p = ffi.new('uns32_ptr')

        if not self.seq_is_set_up:
            self.setup_sequence()

        if fresh_capture:
            pv.exp_start_seq(self.hcam, self.stream_buf)

        t = time.clock()
        tfinal = float('inf') if timeout == -1 else (t + timeout/1000.)
        status = pv.READOUT_NOT_ACTIVE
        while status != pv.READOUT_COMPLETE and status != pv.READOUT_FAILED and t <= tfinal:
            pv.exp_check_status(self.hcam, status_p, byte_cnt_p)
            status = status_p[0]
            t = time.clock()

        if status == pv.READOUT_FAILED:
            raise Exception("Data collection error: {}".format(pv.error_code()))

        if status != pv.READOUT_COMPLETE:
            return None

        # Dump images into the buffer
        pv.exp_finish_seq(self.hcam, self.stream_buf, self.hbuf)
        himg_p = ffi.new('int16_ptr')
        img_addr_p = ffi.new('void_ptr_ptr')
        w_p = ffi.new('int16_ptr')
        h_p = ffi.new('int16_ptr')

        images = []
        for i in range(self.nframes):
            image_regions = []
            for j in range(len(self.regions)):
                pv.buf_get_img_handle(self.hbuf, i, j, himg_p)
                pv.buf_get_img_ptr(himg_p[0], img_addr_p)
                pv.buf_get_img_size(himg_p[0], w_p, h_p)
                img_addr = img_addr_p[0]
                size = w_p[0]*h_p[0]
                buf = ffi.buffer(img_addr, size*2)
                image_regions.append(buf)
            images.append(image_regions)

        if not force_list and self.nframes == 1 and len(self.regions) == 1:
            return images[0][0]

        return images

    def grab_ndarray(self, fresh_capture=True, force_list=False, timeout=-1):
        bufs = self.grab_frame(fresh_capture, force_list=True, timeout=timeout)

        if bufs is None:
            return None

        arrays = []
        for i, per_exposure_bufs in enumerate(bufs):
            per_exposure_arrs = []
            for buf, region in zip(per_exposure_bufs, self.regions):
                x0, x1, xbin, y0, y1, ybin = region
                w, h = (x1-x0+1)/xbin, (y1-y0+1)/ybin
                per_exposure_arrs.append(np.frombuffer(buffer(buf), np.uint16, w*h).reshape((h, w)))
            arrays.append(per_exposure_arrs)

        if not force_list and self.nframes == 1 and len(self.regions) == 1:
            return arrays[0][0]

        return arrays

    def get_param(self, param_id, attrib):
        attr_type_map = {
            pv.ATTR_ACCESS: 'uns16_ptr',
            pv.ATTR_AVAIL: 'rs_bool_ptr',
            pv.ATTR_COUNT: 'uns32_ptr',
            pv.ATTR_CURRENT: None,
            pv.ATTR_DEFAULT: None,
            pv.ATTR_INCREMENT: None,
            pv.ATTR_MAX: None,
            pv.ATTR_MIN: None,
            pv.ATTR_TYPE: 'uns16_ptr'
        }
        param_type_map = {
            pv.TYPE_CHAR_PTR: 'char_ptr',
            pv.TYPE_INT8: 'int8_ptr',
            pv.TYPE_UNS8: 'uns8_ptr',
            pv.TYPE_INT16: 'int16_ptr',
            pv.TYPE_UNS16: 'uns16_ptr',
            pv.TYPE_INT32: 'int32_ptr',
            pv.TYPE_UNS32: 'uns32_ptr',
            pv.TYPE_FLT64: 'flt64_ptr',
            pv.TYPE_ENUM: 'uns32_ptr',
            pv.TYPE_BOOLEAN: 'rs_bool_ptr',
            pv.TYPE_VOID_PTR: 'void_ptr',
            pv.TYPE_VOID_PTR_PTR: 'void_ptr_ptr'
        }
        attr_type = attr_type_map[attrib]
        if attr_type is None:
            param_value = ffi.new('uns16_ptr')
            pv.get_param(self.hcam, param_id, pv.ATTR_TYPE, param_value)
            attr_type = param_type_map[param_value[0]]

        if attr_type == 'char_ptr':
            param_value = ffi.new('uns32_ptr')
            pv.get_param(self.hcam, param_id, pv.ATTR_COUNT, param_value)
            # ATTR_COUNT gives us the length of the string...
            param_value = ffi.new('char[{}]'.format(param_value[0]))
        else:
            param_value = ffi.new(attr_type)

        pv.get_param(self.hcam, param_id, attrib, param_value)

        if attr_type == 'char_ptr':
            result = ffi.string(param_value)
        else:
            result = param_value[0]
        return result

    def _width(self):
        return self.get_param(pv.PARAM_SER_SIZE, pv.ATTR_CURRENT)

    def _height(self):
        return self.get_param(pv.PARAM_PAR_SIZE, pv.ATTR_CURRENT)

    def bit_depth(self):
        return self.get_param(pv.PARAM_BIT_DEPTH, pv.ATTR_CURRENT)

    width = property(_width)
    height = property(_height)


def list_instruments():
    names = PVCam._cam_names()
    cams = []

    for name in names:
        params = _ParamDict("<PVCam '{}'>".format(name))
        params['module'] = 'cameras.pvcam'
        params['pvcam_name'] = name
        cams.append(params)
    return cams


def _instrument(params):
    if 'pvcam_name' in params:
        cam = PVCam(params['pvcam_name'])
    elif params['module'] == 'cameras.pvcam':
        cam = PVCam()
    else:
        raise InstrumentTypeError()

    return cam
