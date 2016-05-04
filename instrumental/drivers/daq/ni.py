# -*- coding: utf-8 -*-
# Copyright 2014-2015 Nate Bogdanowicz
"""
Driver module for NI-DAQmx-supported hardware.
"""

from __future__ import print_function, division, unicode_literals

from collections import OrderedDict
from ctypes import create_string_buffer, c_double, c_int32, c_uint32, byref
import numpy as np
import PyDAQmx as mx

from instrumental import Q_
from . import DAQ
from .. import _ParamDict
from ...errors import Error, InstrumentTypeError

# Make PyDAQmx constants a bit less ridiculously long
for attr in dir(mx):
    if attr.startswith('DAQmx_Val_'):
        setattr(mx, attr[10:], getattr(mx, attr))


def _handle_timing_params(duration, fsamp, n_samples):
    if duration:
        duration = Q_(duration).to('s')
        if fsamp:
            fsamp = Q_(fsamp).to('Hz')
            n_samples = int((duration*fsamp).to(''))  # Exclude endpoint
        else:
            n_samples = int(n_samples or 1000.)
            fsamp = n_samples / duration
    elif fsamp:
        fsamp = Q_(fsamp).to('Hz')
        n_samples = int(n_samples or 1000.)
    return fsamp, n_samples


def _instrument(params):
    if 'nidaq_devname' not in params:
        raise InstrumentTypeError("NIDAQ requires 'nidaq_devname'")
    dev_name = params['nidaq_devname']
    return NIDAQ(dev_name)


class NotSupportedError(Error):
    pass


class Task(object):
    """
    Note that true DAQmx tasks can only include one type of channel (e.g. AI).
    To run multiple synchronized reads/writes, we need to make one task for
    each type, then use the same sample clock for each.
    """
    def __init__(self, *args):
        """Creates a task that uses the given channels.

        Each arg can either be a Channel or a tuple of (Channel, name_str)
        """
        self.channels = OrderedDict()
        self._mxtasks = {}
        self.AOs, self.AIs, self.DOs, self.DIs, self.COs, self.CIs = [], [], [], [], [], []
        TYPED_CHANNELS = {'AO': self.AOs, 'AI': self.AIs, 'DO': self.DOs,
                          'DI': self.DIs, 'CO': self.COs, 'CI': self.CIs}
        for arg in args:
            if isinstance(arg, Channel):
                channel = arg
                name = channel.name
            else:
                channel, name = arg

            if name in self.channels:
                raise Exception("Duplicate channel name {}".format(name))

            if channel.type not in self._mxtasks:
                self._mxtasks[channel.type] = mx.Task()

            self.channels[name] = channel
            channel._add_to_task(self._mxtasks[channel.type])

            TYPED_CHANNELS[channel.type].append(channel)

    def set_timing(self, duration=None, fsamp=None, n_samples=None,
                   mode='finite', clock='', rising=True):
        fsamp, n_samples = _handle_timing_params(duration, fsamp, n_samples)
        fsamp = fsamp.to('Hz').magnitude
        self.fsamp = fsamp
        edge = mx.DAQmx_Val_Rising if rising else mx.DAQmx_Val_Falling
        _sampleMode_map = {
            'finite': mx.DAQmx_Val_FiniteSamps,
            'continuous': mx.DAQmx_Val_ContSamps,
            'hwtimed': mx.DAQmx_Val_HWTimedSinglePoint
        }
        sample_mode = _sampleMode_map[mode]

        master_clock = ''
        master_trig = ''
        self.master_type = None
        for typ in ['AI', 'AO', 'DI', 'DO']:
            if typ in self._mxtasks:
                devname = ''
                for ch in self.channels.values():
                    if ch.type == typ:
                        devname = ch.dev.name
                        break
                master_clock = '/{}/{}/SampleClock'.format(devname, typ.lower())
                master_trig = '/{}/{}/StartTrigger'.format(devname, typ.lower())
                self.master_type = typ
                break

        for typ, task in self._mxtasks.items():
            if typ == self.master_type:
                clock = bytes('')
            else:
                clock = bytes(master_clock)

            task.CfgSampClkTiming(clock, fsamp, edge, sample_mode, n_samples)

        for typ, task in self._mxtasks.items():
            if typ != self.master_type:
                task.CfgDigEdgeStartTrig(master_trig, mx.DAQmx_Val_Rising)

    def run(self, write_data=None):
        # Need to make sure we get data array for each output channel (AO, DO, CO...)
        for ch_name, ch in self.channels.items():
            if ch.type in ('AO', 'DO', 'CO') and ch_name not in write_data:
                raise Exception('write_data missing an array for output channel {}'
                                .format(ch_name))

        # Then set up writes for each channel, don't auto-start
        self._write_AO_channels(write_data)
        # self.write_DO_channels()
        # self.write_CO_channels()

        # Then manually start. Do we need triggering to launch all tasks at the
        # same time? Do we only start the 'main' one? So many questions...
        for typ, mxtask in self._mxtasks.items():
            if typ != self.master_type:
                mxtask.StartTask()
        self._mxtasks[self.master_type].StartTask()  # Start the master last

        # Lastly, read the data (e.g. using ReadAnalogF64)
        read_data = self._read_AI_channels()

        self._mxtasks[self.master_type].StopTask()  # Stop the master first
        for typ, mxtask in self._mxtasks.items():
            if typ != self.master_type:
                mxtask.StopTask()

        return read_data

    def _read_AI_channels(self):
        """ Returns a dict containing the AI buffers. """
        task = self._mxtasks['AI']

        bufsize_per_chan = c_uint32()
        task.GetBufInputBufSize(byref(bufsize_per_chan))
        buf_size = bufsize_per_chan.value * len(self.AIs)

        data = np.zeros(buf_size, dtype=np.float64)
        num_samples_read = c_int32()
        task.ReadAnalogF64(-1, -1.0, mx.DAQmx_Val_GroupByChannel,
                           data, len(data), byref(num_samples_read), None)

        num_samples_read = num_samples_read.value
        res = {}
        for i, ch in enumerate(self.AIs):
            start = i*num_samples_read
            stop = (i+1)*num_samples_read
            res[ch.name] = Q_(data[start:stop], 'V')
        res['t'] = Q_(np.linspace(0, float(num_samples_read-1)/self.fsamp, num_samples_read), 's')
        return res

    def _write_AO_channels(self, data):
        task = self._mxtasks['AO']
        ao_names = [name for (name, ch) in self.channels.items() if ch.type == 'AO']
        arr = np.concatenate([Q_(data[ao]).to('V').magnitude for ao in ao_names])
        arr = arr.astype(np.float64)
        n_samples = data.values()[0].magnitude.size
        n_samples_written = c_int32()
        task.WriteAnalogF64(n_samples, False, -1.0,
                            mx.DAQmx_Val_GroupByChannel, arr,
                            byref(n_samples_written), None)


class _Task(object):
    def __init__(self, dev):
        self.dev = dev
        self.t = mx.Task()
        self.AIs = []
        self.AOs = []
        self.chans = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """Cleanup method for use as a ContextManager"""
        try:
            self.t.StopTask()
        except:
            if value is None:
                # Only raise new error from StopTask start with one
                raise
        finally:
            # Always clean up our memory
            self.t.ClearTask()
            self.dev.tasks.remove(self)

    def stop(self):
        self.t.StopTask()

    def config_timing(self, fsamp, samples, mode='finite', clock='',
                      rising=True):
        _sampleMode_map = {
            'finite': mx.DAQmx_Val_FiniteSamps,
            'continuous': mx.DAQmx_Val_ContSamps,
            'hwtimed': mx.DAQmx_Val_HWTimedSinglePoint
        }
        edge = mx.DAQmx_Val_Rising if rising else mx.DAQmx_Val_Falling
        fsamp = float(Q_(fsamp).to('Hz').magnitude)
        samples = int(samples)
        sample_mode = _sampleMode_map[mode]
        clock = bytes(clock)
        self.t.CfgSampClkTiming(clock, fsamp, edge, sample_mode, samples)
        # Save for later
        self.samples = samples
        self.fsamp = fsamp

    def config_analog_trigger(self, source, trig_level, rising=True, pretrig_samples=2):
        source_name = self._handle_ai(source)
        level_mag = float(Q_(trig_level).to('V').magnitude)
        slope = mx.DAQmx_Val_RisingSlope if rising else mx.DAQmx_Val_FallingSlope
        self.t.CfgAnlgEdgeStartTrig(source_name, slope, level_mag,
                                    pretrig_samples)

    def config_digital_trigger(self, source, rising=True, pretrig_samples=0):
        source_name = self._handle_di(source)
        edge = mx.DAQmx_Val_Rising if rising else mx.DAQmx_Val_Falling
        self.t.CfgDigEdgeRefTrig(source_name, edge, pretrig_samples)

    def _handle_ai(self, ai):
        if isinstance(ai, int):
            s = '{}/ai{}'.format(self.dev.name, ai)
        elif isinstance(ai, basestring):
            if ai.startswith(self.dev.name):
                s = ai
            else:
                s = '{}/{}'.format(self.dev.name, ai)
        return s.encode('ascii')

    def _handle_ao(self, ao):
        if isinstance(ao, int):
            s = '{}/ao{}'.format(self.dev.name, ao)
        elif isinstance(ao, basestring):
            if ao.startswith(self.dev.name):
                s = ao
            else:
                s = '{}/{}'.format(self.dev.name, ao)
        return s.encode('ascii')

    def _handle_di(self, di):
        if isinstance(di, int):
            s = '{}/port{}'.format(self.dev.name, di)
        elif isinstance(di, basestring):
            if di.startswith(self.dev.name):
                s = di
            else:
                s = '{}/{}'.format(self.dev.name, di)
        return s.encode('ascii')

    def _handle_do(self, do):
        if isinstance(do, int):
            s = '{}/port{}'.format(self.dev.name, do)
        elif isinstance(do, basestring):
            if do.startswith(self.dev.name):
                s = do
            else:
                s = '{}/{}'.format(self.dev.name, do)
        return s.encode('ascii')

    def _handle_ch_name(self, ch_name, ai_name):
        return ch_name.encode('ascii') if ch_name else b''

    def _handle_minmax_AI(self, min_val, max_val):
        if min_val is None or max_val is None:
            min_mag, max_mag = self.dev.get_AI_max_range()
        else:
            min_mag = Q_(min_val).to('V').magnitude
            max_mag = Q_(max_val).to('V').magnitude
        return min_mag, max_mag

    def _handle_minmax_AO(self, min_val, max_val):
        if min_val is None or max_val is None:
            min_mag, max_mag = self.dev.get_AO_max_range()
        else:
            min_mag = Q_(min_val).to('V').magnitude
            max_mag = Q_(max_val).to('V').magnitude
        return min_mag, max_mag

    def _handle_timeout(self, timeout):
        if timeout is not None:
            timeout = float(Q_(timeout).to('s').magnitude)
        else:
            timeout = -1.0
        return timeout

    def get_buf_size(self):
        num = c_uint32()
        self.t.GetBufInputBufSize(byref(num))
        return num.value

    def add_DI_channel(self, di):
        di_name = self._handle_di(di)
        self.t.CreateDIChan(di_name, None, mx.DAQmx_Val_ChanForAllLines)

    def add_DO_channel(self, do):
        do_name = self._handle_do(do)
        self.chans.append(do_name)
        self.t.CreateDOChan(do_name, None, mx.DAQmx_Val_ChanForAllLines)

    def add_AI_channel(self, ai, name=None, min_val=None, max_val=None):
        """ Adds an analog input channel (or channels) to the task """
        ai_name = self._handle_ai(ai)
        ch_name = self._handle_ch_name(name, ai_name)
        self.AIs.append(ch_name)
        min_mag, max_mag = self._handle_minmax_AI(min_val, max_val)
        self.t.CreateAIVoltageChan(ai_name, ch_name,
                                   mx.DAQmx_Val_Cfg_Default, min_mag, max_mag,
                                   mx.DAQmx_Val_Volts, None)
        return ch_name

    def add_AO_channel(self, ao, name=None, min_val=None, max_val=None):
        """ Adds an analog output channel (or channels) to the task """
        ao_name = self._handle_ao(ao)
        ch_name = self._handle_ch_name(name, ao_name)
        self.AOs.append(ch_name)
        min_mag, max_mag = self._handle_minmax_AO(min_val, max_val)
        self.t.CreateAOVoltageChan(ao_name, ch_name,
                                   min_mag, max_mag,
                                   mx.DAQmx_Val_Volts, None)
        return ch_name

    def add_AO_funcgen_channel(self, ao, name=None, func=None, fsamp=None, amp=None, offset='0V'):
        """ Adds an analog output funcgen channel (or channels) to the task """
        ao_name = "{}/ao{}".format(self.dev.name, ao).encode('ascii')
        ch_name = 'ao{}'.format(ao) if name is None else name
        ch_name = ch_name.encode('ascii')
        self.AOs.append(ch_name)
        if fsamp is None or amp is None:
            raise Exception("Must include fsamp, and amp")
        fsamp_mag = float(Q_(fsamp).to('Hz').magnitude)
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
                                   fsamp_mag, amp_mag, off_mag)

    def write_AO_channels(self, data, timeout=-1.0, autostart=True):
        if timeout != -1.0:
            timeout = float(Q_(timeout).to('s').magnitude)
        arr = np.concatenate([data[ao].to('V').magnitude for ao in self.AOs]).astype(np.float64)
        n_samples = data.values()[0].magnitude.size
        n_samples_written = c_int32()
        self.t.WriteAnalogF64(n_samples, autostart, timeout,
                              mx.DAQmx_Val_GroupByChannel, arr,
                              byref(n_samples_written), None)

    def write_DO_channels(self, data, channels, timeout=-1.0, autostart=True):
        if timeout != -1.0:
            timeout = float(Q_(timeout).to('s').magnitude)

        arr = self._make_DO_array(data, channels)
        n_samples = arr.size
        n_samples_written = c_int32()
        self.t.WriteDigitalU32(n_samples, autostart, timeout,
                               mx.DAQmx_Val_GroupByChannel, arr,
                               byref(n_samples_written), None)

    def _make_DO_array(self, data, channels):
        """ Get the port ordering in the final integer

        Parameters
        ----------
        data: dict
            Mapping from channel names to per-channel data arrays. Each array is a series of
            integer samples. Each sample is an integer representation of the output state of the
            corresponding channel.
        """
        ports = []
        for ch in channels:
            for port_name, line_name in ch.line_pairs:
                if port_name not in ports:
                    ports.append(port_name)

        # Final int array
        out = np.zeros(len(data.values()[0]), dtype=np.uint32)

        for ch in channels:
            arr = data[ch.name]
            for i, (port_name, line_name) in enumerate(ch.line_pairs):
                line_num = int(line_name[4:])
                bits = np.bitwise_and(arr, (1 << i))  # Mask out the user-input bits

                left_shift_amount = line_num - i
                if left_shift_amount > 0:
                    byts = np.left_shift(bits, left_shift_amount)
                elif left_shift_amount < 0:
                    byts = np.right_shift(bits, -left_shift_amount)
                else:
                    byts = bits

                byte_num = ports.index(port_name)
                out += np.left_shift(byts, 8*byte_num)
        return out

    def write_AO_scalar(self, value, timeout=-1.0):
        if timeout != -1.0:
            timeout = float(Q_(timeout).to('s').magnitude)
        mag = float(Q_(value).to('V').magnitude)
        self.t.WriteAnalogScalarF64(True, timeout, mag, None)

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

        num_samples_read = num_samples_read.value
        res = {}
        for i, ch_name in enumerate(self.AIs):
            start = i*num_samples_read
            stop = (i+1)*num_samples_read
            res[ch_name] = Q_(data[start:stop], 'V')
        res['t'] = Q_(np.linspace(0, num_samples_read/self.fsamp,
                                  num_samples_read, endpoint=False), 's')
        return res

    def read_AI_scalar(self, timeout=-1.0):
        if timeout != -1.0:
            timeout = float(Q_(timeout).to('s').magnitude)

        value = c_double()
        self.t.ReadAnalogScalarF64(timeout, byref(value), None)
        return Q_(value.value, 'V')

    def read_DI_scalar(self, timeout=None):
        timeout = self._handle_timeout(timeout)
        value = c_uint32(1)
        self.t.ReadDigitalScalarU32(timeout, byref(value), None)
        return int(value.value)

    def write_DO_scalar(self, value, timeout=None):
        if timeout is None:
            timeout = -1.0
        else:
            timeout = float(Q_(timeout).to('s').magnitude)
        self.t.WriteDigitalScalarU32(True, timeout, value, None)

    def get_AO_only_onboard_mem(self, channel):
        data = c_uint32()
        self.t.GetAOUseOnlyOnBrdMem(channel, byref(data))
        return bool(data.value)

    def set_AO_only_onboard_mem(self, channel, onboard_only):
        data = c_uint32(onboard_only)
        self.t.SetAOUseOnlyOnBrdMem(channel, data)

    def set_DO_only_onboard_mem(self, channel, onboard_only):
        data = c_uint32(onboard_only)
        self.t.SetDOUseOnlyOnBrdMem(channel, data)


class Channel(object):
    pass


class AnalogIn(Channel):
    def __init__(self, dev, chan_name):
        self.dev = dev
        self.name = chan_name
        self.type = 'AI'
        self.fullname = '{}/{}'.format(dev, chan_name)

    def _add_to_task(self, mx_task):
        min_mag, max_mag = self.dev.get_AI_max_range()
        mx_task.CreateAIVoltageChan(self.fullname, None,
                                    mx.DAQmx_Val_Cfg_Default, min_mag, max_mag,
                                    mx.DAQmx_Val_Volts, None)

    def read(self, duration=None, fsamp=None, n_samples=None):
        """Read one or more analog input samples.

        By default, reads and returns a single sample. If two of `duration`, `fsamp`,
        and `n_samples` are given, an array of samples is read and returned.

        Parameters
        ----------
        duration : Quantity
            How long to read from the analog input, specified as a Quantity.
            Use with `fsamp` or `n_samples`.
        fsamp : Quantity
            The sample frequency, specified as a Quantity. Use with `duration`
            or `n_samples`.
        n_samples : int
            The number of samples to read. Use with `duration` or `fsamp`.

        Returns
        -------
        data : scalar or array Quantity
            The data that was read from analog input.
        """
        with self.dev.create_task() as t:
            t.add_AI_channel(self.name)

            num_specified = sum(int(arg is not None) for arg in (duration, fsamp, n_samples))

            if num_specified == 0:
                data = t.read_AI_scalar()
            elif num_specified == 2:
                fsamp, n_samples = _handle_timing_params(duration, fsamp, n_samples)
                t.config_timing(fsamp, n_samples)
                data = t.read_AI_channels()
            else:
                raise Exception('Must specify either 0 or 2 of duration, fsamp, and n_samples')
        return data


class AnalogOut(Channel):
    def __init__(self, dev, chan_name):
        self.dev = dev
        self.type = 'AO'
        self.name = chan_name
        self.fullname = '{}/{}'.format(dev, chan_name)

    def _add_to_task(self, mx_task):
        min_mag, max_mag = self.dev.get_AO_max_range()
        mx_task.CreateAOVoltageChan(self.fullname, None,
                                    min_mag, max_mag,
                                    mx.DAQmx_Val_Volts, None)

    def _write_scalar(self, value):
        with self.dev.create_task() as t:
            t.add_AO_channel(self.name)
            t.write_AO_scalar(value)

    def read(self, duration=None, fsamp=None, n_samples=None):
        """Read one or more analog output samples.

        Not supported by all DAQ models; requires the appropriate internal channel.

        By default, reads and returns a single sample. If two of `duration`, `fsamp`,
        and `n_samples` are given, an array of samples is read and returned.

        Parameters
        ----------
        duration : Quantity
            How long to read from the analog output, specified as a Quantity.
            Use with `fsamp` or `n_samples`.
        fsamp : Quantity
            The sample frequency, specified as a Quantity. Use with `duration`
            or `n_samples`.
        n_samples : int
            The number of samples to read. Use with `duration` or `fsamp`.

        Returns
        -------
        data : scalar or array Quantity
            The data that was read from analog output.
        """
        with self.dev.create_task() as t:
            internal_channel_name = "_{}_vs_aognd".format(self.name)
            try:
                t.add_AI_channel(internal_channel_name)
            except mx.DAQError as e:
                if e.error != -200170:
                    raise
                raise NotSupportedError("DAQ model does not have the internal channel required "
                                        "to sample the output voltage")

            num_specified = sum(int(arg is not None) for arg in (duration, fsamp, n_samples))

            if num_specified == 0:
                data = t.read_AI_scalar()
            elif num_specified == 2:
                fsamp, n_samples = _handle_timing_params(duration, fsamp, n_samples)
                t.config_timing(fsamp, n_samples)
                data = t.read_AI_channels()
            else:
                raise Exception('Must specify either 0 or 2 of duration, fsamp, and n_samples')
        return data


    def write(self, data, duration=None, reps=None, fsamp=None, freq=None, onboard=True):
        """Write a value or array to the analog output.

        If `data` is a scalar value, it is written to output and the function
        returns immediately. If `data` is an array of values, a buffered write
        is performed, writing each value in sequence at the rate determined by
        `duration` and `fsamp` or `freq`. You must specify either `fsamp` or
        `freq`.

        When writing an array, this function blocks until the output sequence
        has completed.

        Parameters
        ----------
        data : scalar or array Quantity
            The value or values to output, passed in Volt-compatible units.
        duration : Quantity, optional
            Used when writing arrays of data. This is how long the entirety of
            the output lasts, specified as a second-compatible Quantity. If
            `duration` is longer than a single period of data, the waveform
            will repeat. Use either this or `reps`, not both. If neither is
            given, waveform is output once.
        reps : int or float, optional
            Used when writing arrays of data. This is how many times the
            waveform is repeated. Use either this or `duration`, not both. If
            neither is given, waveform is output once.
        fsamp: Quantity, optional
            Used when writing arrays of data. This is the sample frequency,
            specified as a Hz-compatible Quantity. Use either this or `freq`,
            not both.
        freq : Quantity, optional
            Used when writing arrays of data. This is the frequency of the
            *overall waveform*, specified as a Hz-compatible Quantity. Use
            either this or `fsamp`, not both.
        onboard : bool, optional
            Use only onboard memory. Defaults to True. If False, all data will
            be continually buffered from the PC memory, even if it is only
            repeating a small number of samples many times.
        """
        if np.isscalar(data):
            return self._write_scalar(data)

        if (fsamp is None) == (freq is None):
            raise Exception("Need one and only one of 'fsamp' or 'freq'")
        if fsamp is None:
            fsamp = Q_(freq)*len(data)
        else:
            fsamp = Q_(fsamp)

        if (duration is not None) and (reps is not None):
            raise Exception("Can use at most one of `duration` or `reps`, not both")
        if duration is None:
            duration = (reps or 1)*len(data)/fsamp
        fsamp, n_samples = _handle_timing_params(duration, fsamp, len(data))

        with self.dev.create_task() as t:
            t.add_AO_channel(self.name)
            t.set_AO_only_onboard_mem(self.name, onboard)
            t.config_timing(fsamp, n_samples)

            t.write_AO_channels({self.name: data})
            t.t.WaitUntilTaskDone(-1)
            t.t.StopTask()


class Counter(Channel):
    def __init__(self, dev, chan_name):
        self.dev = dev
        self.type = 'CIO'
        self.name = chan_name
        self.fullname = '{}/{}'.format(dev, chan_name)

    def output_pulses(self, freq, duration=None, reps=None, idle_high=False, delay=None,
                      duty_cycle=0.5):
        """Generate digital pulses using the counter.

        Outputs digital pulses with a given frequency and duty cycle.

        This function blocks until the output sequence has completed.

        Parameters
        ----------
        freq : Quantity
            This is the frequency of the pulses, specified as a Hz-compatible Quantity.
        duration : Quantity, optional
            How long the entirety of the output lasts, specified as a second-compatible
            Quantity. Use either this or `reps`, not both. If neither is given, only one pulse is
            generated.
        reps : int, optional
            How many pulses to generate. Use either this or `duration`, not both. If neither is
            given, only one pulse is generated.
        idle_high : bool, optional
            Whether the resting state is considered high or low. Idles low by default.
        delay : Quantity, optional
            How long to wait before generating the first pulse, specified as a second-compatible
            Quantity. Defaults to zero.
        duty_cycle : float, optional
            The width of the pulse divided by the pulse period. The default is a 50% duty cycle.
        """
        idle_state = mx.High if idle_high else mx.Low
        delay = 0 if delay is None else Q_(delay).to('s').magnitude
        freq = Q_(freq).to('Hz').magnitude

        if (duration is not None) and (reps is not None):
            raise Exception("Can use at most one of `duration` or `reps`, not both")
        if reps is None:
            if duration is None:
                reps = 1
            else:
                reps = int(Q_(duration).to('s').magnitude * freq)

        with self.dev.create_task() as t:
            t.t.CreateCOPulseChanFreq(self.fullname, None, mx.Hz, idle_state, delay, freq,
                                      duty_cycle)
            t.t.CfgImplicitTiming(mx.FiniteSamps, reps)
            t.t.StartTask()
            t.t.WaitUntilTaskDone(-1)


class VirtualDigitalChannel(Channel):
    def __init__(self, dev, line_pairs):
        self.dev = dev
        self.line_pairs = line_pairs
        self.direction = None
        self.type = 'DIO'
        self.name = self._generate_name()
        self.num_lines = len(line_pairs)
        self.ports = []
        for port_name, line_name in line_pairs:
            if port_name not in self.ports:
                self.ports.append(port_name)

    def _add_to_task(self, mx_task):
        if self.type not in ('DI', 'DO'):
            raise Exception("VirtualDigitalChannel must have a specified " +
                            "channel type of 'DI' or 'DO' to be added to a " +
                            "task.")

        if self.type == 'DI':
            mx_task.CreateDIChan(self._get_name(), None, mx.DAQmx_Val_ChanForAllLines)
        elif self.type == 'DO':
            mx_task.CreateDOChan(self._get_name(), None, mx.DAQmx_Val_ChanForAllLines)

    def _generate_name(self):
        # Fold up ranges. e.g. 1,2,3,4 -> 1:4
        port_start = None
        line_start, prev_line = None, None
        name = ''
        get_num = lambda s: int(s[4:])
        for port, line in self.line_pairs:
            lineno = get_num(line)
            if port_start is None:
                port_start = get_num(port)
                name += '+port{}.'.format(port_start)

            if line_start is None:
                line_start = lineno
                name += str(line_start)
            elif lineno != prev_line + 1:
                # This line doesn't continue the existing range
                line_start = lineno
                if lineno != line_start:
                    name += ':{}'.format(prev_line)
                name += '+port{}.{}'.format(port_start, line_start)

            prev_line = lineno
        if lineno != line_start:
            name += ':{}'.format(prev_line)

        name = name.replace('.0:7', '')
        return name[1:]

    def _get_name(self):
        """Get DAQmx-style name of this channel"""
        line_strs = [self._get_line_name(lp) for lp in self.line_pairs]
        return ','.join(line_strs)

    def _get_line_name(self, line_pair):
        return '{}/{}/{}'.format(self.dev.name, line_pair[0], line_pair[1])

    def __getitem__(self, key):
        if isinstance(key, slice):
            # Follow NI syntax convention where end of slice is included
            start = 0 if key.start is None else key.start
            stop = len(self.line_pairs) if key.stop is None else key.stop

            if start <= stop:
                stop2 = None if key.stop is None else key.stop+1
                sl = slice(key.start, stop2, 1)
            else:
                stop2 = None if stop == 0 else stop-1
                sl = slice(key.start, stop2, -1)
            pairs = self.line_pairs[sl]
        else:
            pairs = [self.line_pairs[key]]
        return VirtualDigitalChannel(self.dev, pairs)

    def __add__(self, other):
        """Concatenate two VirtualDigitalChannels"""
        if not isinstance(other, VirtualDigitalChannel):
            return NotImplemented
        line_pairs = []
        line_pairs.extend(self.line_pairs)
        line_pairs.extend(other.line_pairs)
        return VirtualDigitalChannel(self.dev, line_pairs)

    def _create_DO_int(self, value):
        """Convert nice value to that required by write_DO_scalar()"""
        out_val = 0
        for i, (port_name, line_name) in enumerate(self.line_pairs):
            line_num = int(line_name.replace('line', ''))
            bit = (value & (1 << i)) >> i
            byte = bit << line_num
            byte_num = self.ports.index(port_name)
            out_val += byte << 8*byte_num
        return out_val

    def _parse_DI_int(self, value):
        if self.num_lines == 1:
            return bool(value)
        else:
            port_bytes = {}
            for i, port_name in enumerate(self.ports):
                byte = ((0xFF << 8*i) & value) >> 8*i
                port_bytes[port_name] = byte

            out = 0
            for i, (port_name, line_name) in enumerate(self.line_pairs):
                line_num = int(line_name.replace('line', ''))
                byte = port_bytes[port_name]
                out += ((byte & (1 << line_num)) >> line_num) << i
            return out

    def read(self):
        with self.dev.create_task() as t:
            t.add_DI_channel(self._get_name())
            data = t.read_DI_scalar()
        return self._parse_DI_int(data)

    def write(self, value):
        """Write a value to the digital output channel

        Parameters
        ----------
        value : int or bool
            An int representing the digital values to write. The lowest bit of
            the int is written to the first digital line, the second to the
            second, and so forth. For a single-line DO channel, can be a bool.
        """
        with self.dev.create_task() as t:
            t.add_DO_channel(self._get_name())
            t.write_DO_scalar(self._create_DO_int(value))

    def write_sequence(self, data, duration=None, reps=None, fsamp=None, freq=None, onboard=True):
        """Write an array of samples to the digital output channel

        Outputs a buffered digital waveform, writing each value in sequence at
        the rate determined by `duration` and `fsamp` or `freq`. You must
        specify either `fsamp` or `freq`.

        This function blocks until the output sequence has completed.

        Parameters
        ----------
        data : array or list of ints or bools
            The sequence of samples to output. For a single-line DO channel,
            samples can be bools.
        duration : Quantity, optional
            How long the entirety of the output lasts, specified as a
            second-compatible Quantity. If `duration` is longer than a single
            period of data, the waveform will repeat. Use either this or
            `reps`, not both. If neither is given, waveform is output once.
        reps : int or float, optional
            How many times the waveform is repeated. Use either this or
            `duration`, not both. If neither is given, waveform is output once.
        fsamp: Quantity, optional
            This is the sample frequency, specified as a Hz-compatible
            Quantity. Use either this or `freq`, not both.
        freq : Quantity, optional
            This is the frequency of the *overall waveform*, specified as a
            Hz-compatible Quantity. Use either this or `fsamp`, not both.
        onboard : bool, optional
            Use only onboard memory. Defaults to True. If False, all data will
            be continually buffered from the PC memory, even if it is only
            repeating a small number of samples many times.
        """
        if (fsamp is None) == (freq is None):
            raise Exception("Need one and only one of 'fsamp' or 'freq'")
        if fsamp is None:
            fsamp = Q_(freq)*len(data)
        else:
            fsamp = Q_(fsamp)

        if (duration is not None) and (reps is not None):
            raise Exception("Can use at most one of `duration` or `reps`, not both")
        if duration is None:
            duration = (reps or 1)*len(data)/fsamp
        fsamp, n_samples = _handle_timing_params(duration, fsamp, len(data))

        with self.dev.create_task() as t:
            t.add_DO_channel(self._get_name())
            t.set_DO_only_onboard_mem(self._get_name(), onboard)
            t.config_timing(fsamp, n_samples, clock='')
            t.write_DO_channels({self.name: data}, [self])
            t.t.WaitUntilTaskDone(-1)

    def as_input(self):
        copy = VirtualDigitalChannel(self.dev, self.line_pairs)
        copy.type = 'DI'
        return copy

    def as_output(self):
        copy = VirtualDigitalChannel(self.dev, self.line_pairs)
        copy.type = 'DO'
        return copy


def list_instruments():
    data = create_string_buffer(1000)
    mx.DAQmxGetSysDevNames(data, 1000)

    dev_names = data.value.split(b',')
    instruments = []
    for dev_name in dev_names:
        dev_name = dev_name.strip("'")
        if not dev_name:
            continue
        params = _ParamDict("<NIDAQ '{}'>".format(dev_name))
        params.module = 'daq.ni'
        params['nidaq_devname'] = dev_name
        instruments.append(params)
    return instruments


# Manually taken from NI's support docs since there doesn't seem to be a DAQmx function to do
# this... This list should include all possible internal channels for each type of device, and some
# of these channels will not exist on a given device.
_internal_channels = {
    mx.DAQmx_Val_MSeriesDAQ:
        ['_aignd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd', '_ao2_vs_aognd', '_ao3_vs_aognd',
         '_calref_vs_aignd', '_aignd_vs_aisense', '_aignd_vs_aisense2', '_calSrcHi_vs_aignd',
         '_calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi',
         '_calSrcMid_vs_aignd', '_calSrcLo_vs_aignd', '_ai0_vs_calSrcHi', '_ai8_vs_calSrcHi',
         '_boardTempSensor_vs_aignd', '_PXI_SCXIbackplane_vs_aignd'],
    mx.DAQmx_Val_XSeriesDAQ:
        ['_aignd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd', '_ao2_vs_aognd', '_ao3_vs_aognd',
         '_calref_vs_aignd', '_aignd_vs_aisense', '_aignd_vs_aisense2', '_calSrcHi_vs_aignd',
         '_calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi',
         '_calSrcMid_vs_aignd', '_calSrcLo_vs_aignd', '_ai0_vs_calSrcHi', '_ai8_vs_calSrcHi',
         '_boardTempSensor_vs_aignd'],
    mx.DAQmx_Val_ESeriesDAQ:
        ['_aognd_vs_aognd', '_aognd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd',
         '_calref_vs_calref', '_calref_vs_aignd', '_ao0_vs_calref', '_ao1_vs_calref',
         '_ao1_vs_ao0', '_boardTempSensor_vs_aignd', '_aignd_vs_aignd', '_caldac_vs_aignd',
         '_caldac_vs_calref', '_PXI_SCXIbackplane_vs_aignd'],
    mx.DAQmx_Val_SSeriesDAQ:
        ['_external_channel', '_aignd_vs_aignd', '_aognd_vs_aognd', '_aognd_vs_aignd',
         '_ao0_vs_aognd', '_ao1_vs_aognd', '_calref_vs_calref', '_calref_vs_aignd',
         '_ao0_vs_calref', '_ao1_vs_calref', '_calSrcHi_vs_aignd', '_calref_vs_calSrcHi',
         '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi', '_calSrcMid_vs_aignd',
         '_calSrcMid_vs_calSrcHi'],
    mx.DAQmx_Val_SCSeriesDAQ:
        ['_external_channel', '_aignd_vs_aignd', '_calref_vs_aignd', '_calSrcHi_vs_aignd',
         '_aignd_vs_calSrcHi', '_calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi',
         '_aipos_vs_calSrcHi', '_aineg_vs_calSrcHi', '_cjtemp0', '_cjtemp1', '_cjtemp2',
         '_cjtemp3', '_cjtemp4', '_cjtemp5', '_cjtemp6', '_cjtemp7', '_aignd_vs_aignd0',
         '_aignd_vs_aignd1'],
    mx.DAQmx_Val_USBDAQ:
        ['_cjtemp', '_cjtemp0', '_cjtemp1', '_cjtemp2', '_cjtemp3'],
    mx.DAQmx_Val_DynamicSignalAcquisition:
        ['_external_channel', '_5Vref_vs_aignd', '_ao0_vs_ao0neg', '_ao1_vs_ao1neg',
         '_aignd_vs_aignd', '_ref_sqwv_vs_aignd'],
    mx.DAQmx_Val_CSeriesModule:
        ['_aignd_vs_aignd', '_calref_vs_aignd', '_cjtemp', '_cjtemp0', '_cjtemp1', '_cjtemp2',
         '_aignd_vs_aisense', 'calSrcHi_vs_aignd', 'calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi',
         '_aignd_vs_calSrcHi', '_calSrcMid_vs_aignd', '_boardTempSensor_vs_aignd',
         '_ao0_vs_calSrcHi', '_ai8_vs_calSrcHi', '_cjtemp3', '_ctr0', '_ctr1', '_freqout', '_ctr2',
         '_ctr3'],
    mx.DAQmx_Val_SCXIModule:
        ['_cjTemp', '_cjTemp0', '_cjTemp1', '_cjTemp2' , '_cjTemp3' , '_cjTemp4' , '_cjTemp5' ,
         '_cjTemp6' , '_cjTemp7', '_pPos0', '_pPos1', '_pPos2', '_pPos3', '_pPos4', '_pPos5',
         '_pPos6', '_pPos7', '_pNeg0', '_pNeg1',  '_pNeg2',  '_pNeg3',  '_pNeg4',  '_pNeg5',
         '_pNeg6',  '_pNeg7', '_Vex0', '_Vex1', '_Vex2', '_Vex3', '_Vex4', '_Vex5', '_Vex6',
         '_Vex7', '_Vex8', '_Vex9', '_Vex10', '_Vex11', '_Vex12', '_Vex13', '_Vex14', '_Vex15',
         '_Vex16', '_Vex17', '_Vex18', '_Vex19', '_Vex20', '_Vex21', '_Vex22', '_Vex23',
         '_IexNeg0', '_IexNeg1', '_IexNeg2', '_IexNeg3', '_IexNeg4', '_IexNeg5', '_IexNeg6',
         '_IexNeg7', '_IexNeg8', '_IexNeg9', '_IexNeg10', '_IexNeg11', '_IexNeg12', '_IexNeg13',
         '_IexNeg14', '_IexNeg15', '_IexNeg16', '_IexNeg17', '_IexNeg18', '_IexNeg19', '_IexNeg20',
         '_IexNeg21', '_IexNeg22', '_IexNeg23', '_IexPos0', '_IexPos1', '_IexPos2', '_IexPos3',
         '_IexPos4', '_IexPos5', '_IexPos6', '_IexPos7', '_IexPos8', '_IexPos9', '_IexPos10',
         '_IexPos11', '_IexPos12', '_IexPos13', '_IexPos14', '_IexPos15', '_IexPos16', '_IexPos17',
         '_IexPos18', '_IexPos19', '_IexPos20', '_IexPos21', '_IexPos22', '_IexPos23'],
    mx.DAQmx_Val_NIELVIS:
        ['_aignd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd', '_calref_vs_aignd',
         '_aignd_vs_aisense', '_aignd_vs_aisense2', '_calSrcHi_vs_aignd', '_calref_vs_calSrcHi',
         '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi', '_calSrcMid_vs_aignd',
         '_calSrcLo_vs_aignd', '_ai0_vs_calSrcHi', '_ai8_vs_calSrcHi', '_boardTempSensor_vs_aignd',
         '_ai16', '_ai17', '_ai18', '_ai19', '_ai20', '_ai21', '_ai22', '_ai23', '_ai24', '_ai25',
         '_ai26', '_ai27', '_ai28', '_ai29', '_ai30', '_ai31', '_vpsPosCurrent', '_vpsNegCurrent',
         '_vpsPos_vs_gnd', '_vpsNeg_vs_gnd', '_dutNeg', '_base', '_dutPos', '_fgenImpedance',
         '_ao0Impedance'],
}


class NIDAQ(DAQ):
    def __init__(self, dev_name):
        """
        Constructor for an NIDAQ object. End users should not use this
        directly, and should instead use
        :py:func:`~instrumental.drivers.instrument`
        """
        self.name = dev_name
        self.tasks = []
        self._load_analog_channels()
        self._load_internal_channels()
        self._load_digital_ports()
        self._load_counters()
        self.mx = mx

        self._param_dict = _ParamDict("<NIDAQ '{}'>".format(dev_name))
        self._param_dict.module = 'daq.ni'
        self._param_dict['nidaq_devname'] = dev_name
        self._param_dict['module'] = 'daq.ni'

    def _load_analog_channels(self):
        for ai_name in self.get_AI_channels():
            setattr(self, ai_name, AnalogIn(self, ai_name))

        for ao_name in self.get_AO_channels():
            setattr(self, ao_name, AnalogOut(self, ao_name))

    def _load_internal_channels(self):
        ch_names = _internal_channels.get(self.get_product_category(), [])
        for ch_name in ch_names:
            setattr(self, ch_name, AnalogIn(self, ch_name))

    def _load_counters(self):
        for c_name in self.get_CI_channels():
            setattr(self, c_name, Counter(self, c_name))

    def __str__(self):
        return self.name

    def _load_digital_ports(self):
        # Need to handle general case of DI and DO ports, can't assume they're
        # always the same...
        ports = {}
        for line_fullname in self.get_DI_lines():
            port_name, line_name = line_fullname.split('/')
            if port_name not in ports:
                ports[port_name] = []
            ports[port_name].append(line_name)

        for port_name, line_names in ports.items():
            line_pairs = [(port_name, l) for l in line_names]
            chan = VirtualDigitalChannel(self, line_pairs)
            setattr(self, port_name, chan)

    def _get_daq_string(self, func, str_len):
        """ Call funcs with the signature (dev_name, data, data_len) """
        data = create_string_buffer(str_len)
        func(self.name, data, str_len)
        return data.value

    def create_task(self):
        task = _Task(self)
        self.tasks.append(task)
        return task

    def get_product_type(self):
        data = create_string_buffer(1000)
        mx.DAQmxGetDevProductType(self.name, data, 1000)
        return data.value

    def get_product_category(self):
        data = c_int32()
        mx.DAQmxGetDevProductCategory(self.name, byref(data))
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
        chan_str = self._get_daq_string(mx.DAQmxGetDevAIPhysicalChans, 1100)
        return [chan.split('/', 1)[1] for chan in chan_str.split(',')]

    def get_AO_channels(self):
        chan_str = self._get_daq_string(mx.DAQmxGetDevAOPhysicalChans, 1100)
        return [chan.split('/', 1)[1] for chan in chan_str.split(',')]

    def get_CI_channels(self):
        chan_str = self._get_daq_string(mx.DAQmxGetDevCIPhysicalChans, 1100)
        return [chan.split('/', 1)[1] for chan in chan_str.split(',')]

    def get_CO_channels(self):
        chan_str = self._get_daq_string(mx.DAQmxGetDevCOPhysicalChans, 1100)
        return [chan.split('/', 1)[1] for chan in chan_str.split(',')]

    def get_DI_ports(self):
        chan_str = self._get_daq_string(mx.DAQmxGetDevDIPorts, 1100)
        return [chan.split('/', 1)[1] for chan in chan_str.split(',')]

    def get_DO_ports(self):
        chan_str = self._get_daq_string(mx.DAQmxGetDevDOPorts, 1100)
        return [chan.split('/', 1)[1] for chan in chan_str.split(',')]

    def get_DI_lines(self):
        line_str = self._get_daq_string(mx.DAQmxGetDevDILines, 1100)
        return [line.split('/', 1)[1] for line in line_str.split(',')]

    def get_DO_lines(self):
        line_str = self._get_daq_string(mx.DAQmxGetDevDOLines, 1100)
        return [line.split('/', 1)[1] for line in line_str.split(',')]

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
