# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz
"""
Driver for Photometrics cameras.
"""

import os.path
import numpy as np
from cffi import FFI
import pvcam_headers
from .. import InstrumentTypeError, InstrumentNotFoundError, _ParamDict

__all__ = ['PVCam']

ffi = FFI()
with open(os.path.join(os.path.dirname(__file__), 'pvcam_clean.h')) as f:
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
for name in dir(pvcam_headers):
    if not name.startswith('__'):
        setattr(pv, name, getattr(pvcam_headers, name))

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


class PVCam(object):
    num_cams_open = 0

    def __init__(self, name=''):
        cam_name = ffi.new('char[{}]'.format(pv.CAM_NAME_LEN), name)
        hcam_p = ffi.new('int16[1]')

        if PVCam.num_cams_open == 0:
            pv.pvcam_init()

        if not name:
            pv.cam_get_name(0, cam_name)

        pv.cam_open(cam_name, hcam_p, lib.OPEN_EXCLUSIVE)
        pv.exp_init_seq()

        self.hcam = hcam_p[0]
        self.seq_is_set_up = False
        PVCam.num_cams_open += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @classmethod
    def _total_cams(cls):
        """The total number of cameras on the system"""
        if cls.num_cams_open == 0:
            pv.pvcam_init()

        total_cams_p = ffi.new('int16_ptr')
        pv.cam_get_total(total_cams_p)

        if cls.num_cams_open == 0:
            pv.pvcam_uninit()
        return total_cams_p[0]

    @classmethod
    def _cam_names(cls):
        """A list of the names of all cameras on the system"""
        if cls.num_cams_open == 0:
            pv.pvcam_init()
        cls.num_cams_open += 1  # Fool _total_cams() so we don't have to reinit

        total = PVCam._total_cams()
        cam_name = ffi.new('char[{}]'.format(pv.CAM_NAME_LEN))

        names = []
        for i in range(total):
            pv.cam_get_name(i, cam_name)
            names.append(ffi.string(cam_name))

        cls.num_cams_open -= 1
        if cls.num_cams_open == 0:
            pv.pvcam_uninit()

        return names

    def close(self):
        if self.seq_is_set_up:
            self._unsetup_sequence()
        pv.cam_close(self.hcam)

        PVCam.num_cams_open -= 1
        if PVCam.num_cams_open == 0:
            pv.pvcam_uninit()

    def setup_sequence(self, exp_time=100, nframes=1, mode='timed'):
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
            pv.exp_finish_seq(self.hcam, self.frame, 0)

        mode_map = {
            'timed': pv.TIMED_MODE,
            'variable': pv.VARIABLE_TIMED_MODE,
            'trigger': pv.TRIGGER_FIRST_MODE,
            'strobed': pv.STROBED_MODE,
            'bulb': pv.BULB_MODE,
            'flash': pv.FLASH_MODE
        }
        mode = mode_map[mode]

        w, h = self.width(), self.height()
        region_p = ffi.new('rgn_type *', (0, w-1, 1, 0, h-1, 1))
        size_p = ffi.new('uns32 *')

        n_exposures = nframes
        n_regions = 1
        pv.exp_setup_seq(self.hcam, n_exposures, n_regions, region_p, mode,
                         exp_time, size_p)

        # size_p[0] is the number of BYTES in the pixel stream
        self.frame = ffi.new('uns16[{}]'.format(size_p[0]/2))
        self.seq_is_set_up = True
        self.nframes = nframes

    def _unsetup_sequence(self):
        pv.exp_finish_seq(self.hcam, self.frame, 0)
        pv.exp_uninit_seq()

    def grab_frame(self):
        status_p = ffi.new('int16_ptr')
        byte_cnt_p = ffi.new('uns32_ptr')
        pv.exp_start_seq(self.hcam, self.frame)

        status = pv.READOUT_NOT_ACTIVE
        while status != pv.READOUT_COMPLETE and status != pv.READOUT_FAILED:
            pv.exp_check_status(self.hcam, status_p, byte_cnt_p)
            status = status_p[0]

        if status == pv.READOUT_FAILED:
            raise Exception("Data collection error: {}".format(pv.error_code()))

        return self.frame

    def grab_ndarray(self):
        buf = ffi.buffer(self.grab_frame())
        w, h = self.width(), self.height()
        f_nbytes = w*h*2

        images = []
        for i in range(self.nframes):
            arr = np.frombuffer(buf[i*f_nbytes:(i+1)*f_nbytes], np.uint16)
            arr = arr.reshape((h, w))
            images.append(arr)

        if len(images) == 1:
            return images[0]
        return images

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

    def width(self):
        return self.get_param(pv.PARAM_SER_SIZE, pv.ATTR_CURRENT)

    def height(self):
        return self.get_param(pv.PARAM_PAR_SIZE, pv.ATTR_CURRENT)

    def bit_depth(self):
        return self.get_param(pv.PARAM_BIT_DEPTH, pv.ATTR_CURRENT)


def list_instruments():
    names = PVCam._cam_names()
    cams = []

    for name in names:
        params = _ParamDict("<PVCam '{}'>".format(name))
        params.module = 'cameras.pvcam'
        params['pvcam_name'] = name
        cams.append(params)
    return cams


def _instrument(params):
    if 'pvcam_name' in params:
        cam = PVCam(params['pvcam_name'])
    elif params.module == 'cameras.pvcam':
        cam = PVCam()
    else:
        raise InstrumentTypeError()

    return cam
