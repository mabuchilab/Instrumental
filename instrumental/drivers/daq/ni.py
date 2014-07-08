# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz
"""
Driver module for NI-DAQmx-supported hardware.
"""

from __future__ import print_function

from ctypes import create_string_buffer, c_double, c_int32, c_uint32, byref
import numpy as np
import PyDAQmx as mx

from instrumental import Q_
from . import DAQ
from .. import InstrumentTypeError, _ParamDict, _acceptable_params


def _instrument(params):
    if 'nidaq_devname' not in params:
        raise InstrumentTypeError("NIDAQ requires 'nidaq_devname'")
    dev_name = params['nidaq_devname']
    return NIDAQ(dev_name)


class ITask(object):
    def __init__(self, dev):
        self.dev = dev
        self.t = mx.Task()
        self.AIs = []
        self.AOs = []

    def config_timing(self, rate, samples, mode='finite', clock='',
                      rising=True):
        _sampleMode_map = {
            'finite': mx.DAQmx_Val_FiniteSamps,
            'continuous': mx.DAQmx_Val_ContSamps,
            'hwtimed': mx.DAQmx_Val_HWTimedSinglePoint
        }
        edge = mx.DAQmx_Val_Rising if rising else mx.DAQmx_Val_Falling
        rate = float(Q_(rate).to('Hz').magnitude)
        samples = int(samples)
        sample_mode = _sampleMode_map[mode]
        clock = bytes(clock)
        self.t.CfgSampClkTiming(clock, rate, edge, sample_mode, samples)
        # Save for later
        self.samples = samples
        self.rate = rate

    def _handle_ai(self, ai):
        if isinstance(ai, int):
            s ='{}/ai{}'.format(self.dev.name, ai)
        elif isinstance(ai, basestring):
            if ai.startswith(self.dev.name):
                s = ai
            else:
                s = '{}/{}'.format(self.dev.name, ai)
        return s.encode('ascii')

    def _handle_ch_name(self, ch_name, ai_name):
        if ch_name:
            return ch_name.encode('ascii')
        else:
            return ai_name.rsplit('/', 1)[-1].encode('ascii')

    def _handle_minmax(self, min_val, max_val):
        if min_val is None or max_val is None:
            min_mag, max_mag = self.dev.get_AI_max_range()
        else:
            min_mag = Q_(min_val).to('V').magnitude
            max_mag = Q_(max_val).to('V').magnitude
        return min_mag, max_mag

    def add_AI_channel(self, ai, name=None, min_val=None, max_val=None):
        """ Adds an analog input channel (or channels) to the task """
        ai_name = self._handle_ai(ai)
        ch_name = self._handle_ch_name(name, ai_name)
        self.AIs.append(ch_name)
        min_mag, max_mag = self._handle_minmax(min_val, max_val)
        self.t.CreateAIVoltageChan(ai_name, ch_name,
                                   mx.DAQmx_Val_Cfg_Default, min_mag, max_mag,
                                   mx.DAQmx_Val_Volts, None)
        return ch_name

    def add_AO_channel(self, ao_num, name=None, min_val=None, max_val=None):
        """ Adds an analog output channel (or channels) to the task """
        ao_name = "{}/ao{}".format(self.dev.name, ao_num).encode('ascii')
        name = 'ao{}'.format(ao_num) if name is None else name
        name = name.encode('ascii')
        self.AOs.append(name)
        if min_val is None or max_val is None:
            min_mag, max_mag = self.dev.get_AO_max_range()
        else:
            min_mag = Q_(min_val).to('V').magnitude
            max_mag = Q_(max_val).to('V').magnitude
        self.t.CreateAOVoltageChan(ao_name, name,
                                   min_mag, max_mag,
                                   mx.DAQmx_Val_Volts, None)
        return name

    def add_AO_funcgen_channel(self, ao, name=None, func=None, freq=None, amp=None, offset='0V'):
        """ Adds an analog output funcgen channel (or channels) to the task """
        ao_name = "{}/ao{}".format(self.dev.name, ao).encode('ascii')
        ch_name = 'ao{}'.format(ao) if name is None else name
        ch_name = ch_name.encode('ascii')
        self.AOs.append(ch_name)
        if freq is None or amp is None:
            raise Exception("Must include freq, and amp")
        freq_mag = float(Q_(freq).to('Hz').magnitude)
        amp_mag = float(Q_(amp).to('V').magnitude)
        off_mag = float(Q_(offset).to('V').magnitude)

        func_map = {
            'sin': mx.DAQmx_Val_Sine,
            'tri': mx.DAQmx_Val_Triangle,
            'squ': mx.DAQmx_Val_Square,
            'saw': mx.DAQmx_Val_Sawtooth
        }
        func = func_map[func]
        self.t.CreateAOFuncGenChan(ao_name, ch_name, func,
                                   freq_mag, amp_mag, off_mag)

    def write_AO_channels(self, data, timeout=-1.0, autostart=True):
        if timeout != -1.0:
            timeout = float(Q_(timeout).to('s').magnitude)
        arr = np.concatenate([data[ao].to('V').magnitude for ao in self.AOs]).astype(np.float64)
        samples = data.values()[0].magnitude.size
        samples_written = c_int32()
        self.t.WriteAnalogF64(samples, autostart, timeout,
                              mx.DAQmx_Val_GroupByChannel, arr,
                              byref(samples_written), None)

    def read_AI_channels(self, samples=-1, timeout=-1.0):
        """ Returns a dict containing the AI buffers. """
        samples = int(samples)
        if timeout != -1.0:
            timeout = float(Q_(timeout).to('s').magnitude)

        if samples == -1:
            buf_size = self.get_buf_size()*len(self.AIs)
        else:
            buf_size = samples*len(self.AIs)

        data = np.zeros(buf_size, dtype=np.float64)
        num_samples_read = c_int32()
        self.t.ReadAnalogF64(samples, timeout, mx.DAQmx_Val_GroupByChannel,
                             data, len(data), byref(num_samples_read), None)
        #data = data.reshape(len(self.AIs), -1)
        num_samples_read = num_samples_read.value
        res = {}
        for i, ch_name in enumerate(self.AIs):
            start = i*num_samples_read
            stop = (i+1)*num_samples_read
            res[ch_name] = Q_(data[start:stop], 'V')
        res['t'] = Q_(np.linspace(0, num_samples_read/self.rate, num_samples_read,
                                  endpoint=False), 's')
        return res

    def get_buf_size(self):
        num = c_uint32()
        self.t.GetBufInputBufSize(byref(num))
        return num.value


def list_instruments():
    data = create_string_buffer(1000)
    mx.DAQmxGetSysDevNames(data, 1000)
    dev_names = data.value.split(b',')
    instruments = []
    for dev_name in dev_names:
        dev_name = dev_name.strip("'")
        params = _ParamDict("<NIDAQ '{}'>".format(dev_name))
        params.module = 'daq.ni'
        params['nidaq_devname'] = dev_name
        instruments.append(params)
    return instruments

class NIDAQ(DAQ):
    def __init__(self, dev_name):
        """
        Constructor for an NIDAQ object. End users should not use this
        directly, and should instead use
        :py:func:`~instrumental.drivers.instrument`
        """
        self.name = dev_name
        self.tasks = []

    def _get_daq_string(self, func, str_len):
        """ Call funcs with the signature (dev_name, data, data_len) """
        data = create_string_buffer(str_len)
        func(self.name, data, str_len)
        return data.value

    def create_task(self):
        task = ITask(self)
        self.tasks.append(task)
        return task

    def get_product_type(self):
        data = create_string_buffer(1000)
        mx.DAQmxGetDevProductType(self.name, data, 1000)
        return data.value

    def get_serial(self):
        serial = c_uint32()
        mx.DAQmxGetDevSerialNum(self.name, byref(serial))
        return serial.value

    def get_chassis_num(self):
        num = c_uint32()
        mx.DAQmxGetDevPXIChassisNum(self.name, byref(num))
        return num.value

    def get_slot_num(self):
        num = c_uint32()
        mx.DAQmxGetDevPXISlotNum(self.name, byref(num))
        return num.value

    def get_terminals(self):
        data = create_string_buffer(10000)
        mx.DAQmxGetDevTerminals(self.name, data, 10000)
        return data.value

    def get_AI_channels(self):
        return self._get_daq_string(mx.DAQmxGetDevAIPhysicalChans, 1100)

    def get_AO_channels(self):
        return self._get_daq_string(mx.DAQmxGetDevAOPhysicalChans, 1100)

    def get_CI_channels(self):
        return self._get_daq_string(mx.DAQmxGetDevCIPhysicalChans, 1100)

    def get_CO_channels(self):
        return self._get_daq_string(mx.DAQmxGetDevCOPhysicalChans, 1100)

    def get_DI_ports(self):
        return self._get_daq_string(mx.DAQmxGetDevDIPorts, 1100)

    def get_DO_ports(self):
        return self._get_daq_string(mx.DAQmxGetDevDOPorts, 1100)

    def get_DI_lines(self):
        return self._get_daq_string(mx.DAQmxGetDevDILines, 1100)

    def get_DO_lines(self):
        return self._get_daq_string(mx.DAQmxGetDevDOLines, 1100)

    def get_AI_ranges(self):
        size = 20
        data = (c_double*size)()
        mx.DAQmxGetDevAIVoltageRngs(self.name, data, size)
        pairs = []
        for i in range(0, size, 2):
            if data[i] == 0 and data[i+1] == 0:
                break
            pairs.append((data[i], data[i+1]))
        return pairs

    def get_AI_max_range(self):
        """ Returns the min and max voltage of the widest AI range """
        pairs = self.get_AI_ranges()
        max_pair = (0, 0)
        max_diff = 0
        for pair in pairs:
            diff = abs(pair[1]-pair[0])
            if diff > max_diff:
                max_pair = pair
                max_diff = diff
        return max_pair

    def get_AO_ranges(self):
        size = 20
        data = (c_double*size)()
        mx.DAQmxGetDevAOVoltageRngs(self.name, data, size)
        pairs = []
        for i in range(0, size, 2):
            if data[i] == 0 and data[i+1] == 0:
                break
            pairs.append((data[i], data[i+1]))
        return pairs

    def get_AO_max_range(self):
        """ Returns the min and max voltage of the widest AO range """
        pairs = self.get_AO_ranges()
        max_pair = (0, 0)
        max_diff = 0
        for pair in pairs:
            diff = abs(pair[1]-pair[0])
            if diff > max_diff:
                max_pair = pair
                max_diff = diff
        return max_pair
