# -*- coding: utf-8 -*-
# Copyright 2013-2019 Nate Bogdanowicz
"""
Driver module for Tektronix oscilloscopes.
"""
import datetime as dt

import visa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError

from . import Scope
from .. import VisaMixin, SCPI_Facet, Facet
from ..util import visa_context
from ...util import to_str
from ...errors import Error
from ... import u, Q_


MODEL_CHANNELS = {
    'TDS 210': 2,
    'TDS 220': 2,
    'TDS 224': 4,
    'TDS 1001B': 2,
    'TDS 1002B': 2,
    'TDS 1012B': 2,
    'TDS 2002B': 2,
    'TDS 2004B': 4,
    'TDS 2012B': 2,
    'TDS 2014B': 4,
    'TDS 2022B': 2,
    'TDS 2024B': 4,
    'TDS 3012': 2,
    'TDS 3012B': 2,
    'TDS 3012C': 2,
    'TDS 3014': 4,
    'TDS 3014B': 4,
    'TDS 3014C': 4,
    'TDS 3032': 2,
    'TDS 3032B': 2,
    'TDS 3032C': 2,
    'TDS 3034': 4,
    'TDS 3034B': 4,
    'TDS 3034C': 4,
    'TDS 3052': 2,
    'TDS 3052B': 2,
    'TDS 3052C': 2,
    'TDS 3054': 4,
    'TDS 3054B': 4,
    'TDS 3054C': 4,
    'MSO2012': 2,
    'DPO2012': 2,
    'MSO2014': 4,
    'DPO2014': 4,
    'MSO2024': 4,
    'DPO2024': 4,
    'MSO4032': 2,
    'DPO4032': 2,
    'MSO4034': 4,
    'DPO4034': 4,
    'MSO4054': 4,
    'DPO4054': 4,
    'MSO4104': 4,
    'DPO4104': 4,
}


class ClippingError(Error):
    pass


def infer_termination(msg_str):
    if msg_str.endswith('\r\n'):
        return '\r\n'
    elif msg_str.endswith('\r'):
        return '\r'
    elif msg_str.endswith('\n'):
        return '\n'
    return None


def strstr(value):
    """Convert to str and strip outer quotes"""
    return to_str(value)[1:-1]


def ChannelFacet(msg, convert=None, readonly=False, **kwds):
    get_msg = msg + '?'
    set_msg = None if readonly else msg + ' {}'
    if convert:
        def fget(ch):
            return convert(ch.scope.query(get_msg, ch.num))
    else:
        def fget(ch):
            return ch.scope.query(get_msg, ch.num)

    if set_msg is None:
        fset = None
    elif convert:
        def fset(ch, value):
            ch.scope.write(set_msg, ch.num, convert(value))
    else:
        def fset(ch, value):
            ch.scope.write(set_msg, ch.num, value)

    return Facet(fget, fset, **kwds)


class ChannelProperty(object):
    def __init__(self):
        self.facets = []

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        return Channels(obj, self.facets)

    def __set__(self, obj, qty):
        pass

    def facet(self, facet):
        self.facets.append(facet)
        return facet


class Channels(object):
    def __init__(self, scope, facets):
        self.scope = scope
        self.valid_nums = tuple(range(1, 1+scope.channels))

    def __getitem__(self, key):
        if key not in self.valid_nums:
            raise ValueError('Invalid channel {}. Must be in {!r}'.format(key, self.valid_nums))
        return Channel(self.scope, key)


class Channel(object):
    def __init__(self, scope, num):
        self.scope = scope
        self.num = num

    def __repr__(self):
        return '<Channel {} of {}>'.format(self.num, self.scope)

    scale = ChannelFacet('ch{}:scale', convert=float, units='V')
    offset = ChannelFacet('ch{}:offset', convert=float, units='V')
    position = ChannelFacet('ch{}:position', convert=float)


class TekScope(Scope, VisaMixin):
    """
    A base class for Tektronix scopes. Supports at least TDS 3000 series as
    well as MSO/DPO 4000 series scopes.
    """
    def _initialize(self):
        if self.interface_type == InterfaceType.asrl:
            terminator = self.query('RS232:trans:term?').strip()
            self._rsrc.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
        elif self.interface_type == InterfaceType.usb:
            msg = self.query('*IDN?')
            self._rsrc.read_termination = infer_termination(msg)
        elif self.interface_type == InterfaceType.tcpip:
            msg = self.query('*IDN?')
            self._rsrc.read_termination = infer_termination(msg)
        else:
            pass

        self.write("header OFF")

    def _waveform_params(self):
        return {
            'xin': float(self.query("wfmpre:xincr?")),
            'ymu': float(self.query("wfmpre:ymult?")),
            'xze': float(self.query("wfmpre:xzero?")),
            'yze': float(self.query("wfmpre:yzero?")),
            'pt_o': float(self.query("wfmpre:pt_off?")),
            'yof': float(self.query("wfmpre:yoff?")),
            'xun': strstr(self.query("wfmpre:xun?")),
            'yun': strstr(self.query("wfmpre:yun?")),
        }

    def get_data(self, channel=1, width=2):
        """Retrieve a trace from the scope.

        Pulls data from channel `channel` and returns it as a tuple ``(t,y)``
        of unitful arrays.

        Parameters
        ----------
        channel : int, optional
            Channel number to pull trace from. Defaults to channel 1.
        width : int, optional
            Number of bytes per sample of data pulled from the scope. 1 or 2.

        Returns
        -------
        t, y : pint.Quantity arrays
            Unitful arrays of data from the scope. ``t`` is in seconds, while
            ``y`` is in volts.
        """
        if width not in (1, 2):
            raise ValueError('width must be 1 or 2')

        with self.transaction():
            self.write("data:source ch{}".format(channel))
            try:
                # scope *should* truncate this to record length if it's too big
                stop = self.max_waveform_length
            except AttributeError:
                stop = 1000000
            self.write("data:width {}", width)
            self.write("data:encdg RIBinary")
            self.write("data:start 1")
            self.write("data:stop {}".format(stop))

        #self.resource.flow_control = 1  # Soft flagging (XON/XOFF flow control)
        raw_data_y = self._read_curve(width=width)
        raw_data_x = np.arange(1, len(raw_data_y)+1)

        # Get scale and offset factors
        wp = self._waveform_params()
        x_units = self._tek_units(wp['xun'])
        y_units = self._tek_units(wp['yun'])

        data_x = Q_((raw_data_x - wp['pt_o'])*wp['xin'] + wp['xze'], x_units)
        data_y = Q_((raw_data_y - wp['yof'])*wp['ymu'] + wp['yze'], y_units)

        return data_x, data_y

    @staticmethod
    def _tek_units(unit_str):
        unit_map = {
            'U': '',
            'Volts': 'V'
        }

        unit_str = unit_map.get(unit_str, unit_str)
        try:
            units = u.parse_units(unit_str)
        except UndefinedUnitError:
            units = u.dimensionless
        return units

    def _read_curve(self, width):
        with self.resource.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT),\
            visa_context(self.resource, timeout=10000, read_termination=None,
                         end_input=visa.constants.SerialTermination.none):

            self.write("curve?")
            visalib = self.resource.visalib
            session = self.resource.session

            # NB: Must take slice of bytes returned by visalib.read,
            # to keep from autoconverting to int
            width_byte = visalib.read(session, 2)[0][1:]  # read first 2 bytes
            num_bytes = int(visalib.read(session, int(width_byte))[0])
            buf = bytearray(num_bytes)
            cursor = 0

            while cursor < num_bytes:
                raw_bin, _ = visalib.read(session, num_bytes-cursor)
                buf[cursor:cursor+len(raw_bin)] = raw_bin
                cursor += len(raw_bin)

        self.resource.read()  # Eat termination

        num_points = int(num_bytes // width)
        dtype = '>i{:d}'.format(width)
        return np.frombuffer(buf, dtype=dtype, count=num_points)

    def set_measurement_params(self, num, mtype, channel):
        """Set the parameters for a measurement.

        Parameters
        ----------
        num : int
            Measurement number to set, from 1-4.
        mtype : str
            Type of the measurement, e.g. 'amplitude'
        channel : int
            Number of the channel to measure.
        """
        prefix = 'measurement:meas{}'.format(num)
        self.write("{}:type {};source ch{}".format(prefix, mtype, channel))

    def read_measurement_stats(self, num):
        """
        Read the value and statistics of a measurement.

        Parameters
        ----------
        num : int
            Number of the measurement to read from, from 1-4

        Returns
        -------
        stats : dict
            Dictionary of measurement statistics. Includes value, mean, stddev,
            minimum, maximum, and nsamps.
        """
        prefix = 'measurement:meas{}'.format(num)

        if not self.are_measurement_stats_on():
            raise Exception("Measurement statistics are turned off, "
                            "please turn them on.")

        # Potential issue: If we query for all of these values in one command,
        # are they guaranteed to be taken from the same statistical set?
        # Perhaps we should stop_acquire(), then run_acquire()...
        keys = ['value', 'mean', 'stddev', 'minimum', 'maximum']
        res = self.query(prefix+':value?;mean?;stddev?;minimum?;maximum?;count?;units?').split(';')
        units = res.pop(-1).strip('"')
        count = int(res.pop(-1))
        stats = {k: Q_(rval+units) for k, rval in zip(keys, res)}
        stats['count'] = count

        num_samples = int(self.query('measurement:statistics:weighting?'))
        stats['nsamps'] = num_samples
        return stats

    def read_measurement_value(self, num):
        """Read the value of a measurement.

        Parameters
        ----------
        num : int
            Number of the measurement to read from, from 1-4

        Returns
        -------
        value : pint.Quantity
            Value of the measurement
        """
        prefix = 'measurement:meas{}'.format(num)

        self.read_events()  # Clear the queue
        raw_value, raw_units = self.query('{}:value?;units?'.format(prefix)).split(';')
        units = raw_units.strip('"')

        for code, message in self.read_events():
            if code in (547, 548, 549):
                raise ClippingError(message)

        return Q_(raw_value+units)

    def measure(self, channel, meas_type):
        """Perform immediate measurement."""
        msg = self.query(':measu:immed:source1 ch{};type {};value?;units?'
                         ''.format(channel, meas_type))
        val_str, unit_str = msg.split(';')
        units = self._tek_units(unit_str.strip('"'))

        for code, message in self.read_events():
            if code in (547, 548, 549):
                raise ClippingError(message)

        return Q_(float(val_str), units)

    def set_math_function(self, expr):
        """Set the expression used by the MATH channel.

        Parameters
        ----------
        expr : str
            a string representing the MATH expression, using channel variables
            CH1, CH2, etc. eg. 'CH1/CH2+CH3'
        """
        self.write("math:type advanced")
        self.write('math:define "{}"'.format(expr))

    def get_math_function(self):
        return self.query("math:define?").strip('"')

    def run_acquire(self):
        """Sets the acquire state to 'run'"""
        self.write("acquire:state run")

    def stop_acquire(self):
        """Sets the acquire state to 'stop'"""
        self.write("acquire:state stop")

    @property
    def interface_type(self):
        return self.resource.interface_type

    @property
    def model(self):
        _, model, _, _ = self.query('*IDN?').split(',', 3)
        return model

    @property
    def channels(self):
        try:
            return MODEL_CHANNELS[self.model]
        except KeyError:
            raise KeyError('Unknown number of channels for this scope model')

    def read_events(self):
        """Get a list of events from the Event Queue

        Returns
        -------
        A list of (int, str) pairs containing the code and message for each event in the scope's
        event queue.
        """
        events = []
        while True:
            event_info = self.query('evmsg?').split(',', 1)
            code = int(event_info[0])
            message = event_info[1][1:-1]
            if code == 0:
                break
            elif code == 1:
                self.query('*ESR?')  # Reload event queue
            else:
                events.append((code, message))
        return events

    @property
    def _datetime(self):
        resp = self.query(':date?;:time?')
        return dt.datetime.strptime(resp, '"%Y-%m-%d";"%H:%M:%S"')

    @_datetime.setter
    def _datetime(self, value):
        if not isinstance(value, dt.datetime):
            raise TypeError('value must be a datetime object')
        message = value.strftime(':date "%Y-%m-%d";:time "%H:%M:%S"')
        self.write(message)

    horizontal_scale = SCPI_Facet('hor:main:scale', convert=float, units='s')
    horizontal_delay = SCPI_Facet('hor:delay:pos', convert=float, units='s')
    math_function = property(get_math_function, set_math_function)


class StatScope(TekScope):
    def are_measurement_stats_on(self):
        """Returns whether measurement statistics are currently enabled"""
        res = self.query("measu:statistics:mode?")
        return res not in ['OFF', '0']

    def enable_measurement_stats(self, enable=True):
        """Enables measurement statistics.

        When enabled, measurement statistics are kept track of, including
        'mean', 'stddev', 'minimum', 'maximum', and 'nsamps'.

        Parameters
        ----------
        enable : bool
            Whether measurement statistics should be enabled
        """
        # For some reason, the DPO 4034 uses ALL instead of ON
        self.write("measu:statistics:mode {}".format('ALL' if enable else 'OFF'))

    def disable_measurement_stats(self):
        """Disables measurement statistics"""
        self.enable_measurement_stats(False)

    def set_measurement_nsamps(self, nsamps):
        """Sets the number of samples used to compute measurements.

        Parameters
        ----------
        nsamps : int
            Number of samples used to compute measurements
        """
        self.write("measu:stati:weighting {}".format(nsamps))


class TDS_200(TekScope):
    """A Tektronix TDS 200 series oscilloscope"""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 210', 'TDS 220', 'TDS 224'])


class TDS_1000(TekScope):
    """A Tektronix TDS 1000 series oscilloscope"""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 1001B', 'TDS 1002B', 'TDS 1012B'])


class TDS_2000(TekScope):
    """A Tektronix TDS 2000 series oscilloscope"""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 2002B', 'TDS 2004B',
                                      'TDS 2012B', 'TDS 2014B',
                                      'TDS 2022B', 'TDS 2024B'])


class TDS_3000(StatScope):
    """A Tektronix TDS 3000 series oscilloscope."""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 3012', 'TDS 3012B', 'TDS 3012C',
                                      'TDS 3014', 'TDS 3014B', 'TDS 3014C',
                                      'TDS 3032', 'TDS 3032B', 'TDS 3032C',
                                      'TDS 3034', 'TDS 3034B', 'TDS 3034C',
                                      'TDS 3052', 'TDS 3052B', 'TDS 3052C',
                                      'TDS 3054', 'TDS 3054B', 'TDS 3054C',])

    max_waveform_length = 10000
    waveform_length = SCPI_Facet('wfmpre:nr_pt', convert=int, readonly=True,
                                 doc="Record length of the source waveform")
    datetime = TekScope._datetime


class MSO_DPO_2000(StatScope):
    """A Tektronix MSO/DPO 2000 series oscilloscope."""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['MSO2012', 'MSO2014', 'MSO2024',
                                      'DPO2012', 'DPO2014', 'DPO2024',])

    max_waveform_length = 1250000
    waveform_length = SCPI_Facet('wfmoutpre:recordlength', convert=int, readonly=True,
                                 doc="Record length of the source waveform")
    datetime = TekScope._datetime

    def _waveform_params(self):
        return self._unpack_wfm_params(self.query('wfmoutpre?').split(';'))

    @staticmethod
    def _unpack_wfm_params(param_strs):
        return {key:f(val) for val,(key,f) in
                zip(param_strs,
                    [('byt_n', int),
                     ('bit_n', int),
                     ('enc', to_str),
                     ('bn_f', to_str),
                     ('byt_o', to_str),
                     ('wfi', strstr),
                     ('nr_p', int),
                     ('pt_f', to_str),
                     ('xun', strstr),
                     ('xin', float),
                     ('xze', float),
                     ('pt_o', int),
                     ('yun', strstr),
                     ('ymu', float),
                     ('yof', float),
                     ('yze', float),
                     ('comp', to_str),
                     ('reco', int),
                     ('filterf', int)])}

    ch = ChannelProperty()
    meas = ChannelProperty()

    meas.facet(SCPI_Facet('measu:meas{}:type'))

    def set_min_window(self, width):
        width_s = Q_(width).m_as('s')
        mantissa, exponent = (float(x) for x in format(width_s, 'e').split('e'))
        if mantissa <= 2:
            scale_s = 0.2 * 10.**exponent
        elif mantissa <= 4:
            scale_s = 0.4 * 10.**exponent
        else:
            scale_s = 10.**exponent
        scale_s = max(2e-9, scale_s)
        scale_s = min(100., scale_s)
        self.write('hor:scale {:E}', scale_s)


class MSO_DPO_4000(StatScope):
    """A Tektronix MSO/DPO 4000 series oscilloscope."""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['MSO4032', 'DPO4032', 'MSO4034', 'DPO4034',
                                      'MSO4054', 'DPO4054', 'MSO4104', 'DPO4104',])
    datetime = TekScope._datetime


def load_csv(filename):
    """Load CSV data produced by a Tektronix oscilloscope.

    *Only developed and tested on CSV data generated by a TDS1001B*
    """
    import csv
    info = {}
    x_mag, y_mag = [], []
    with open(filename, 'rt', newline='') as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            key, value, _, x, y = row[:5]
            if key:
                info[key] = value

            x_mag.append(float(x))
            y_mag.append(float(y))

        x_units = u.parse_units(info['Horizontal Units'])
        y_units = u.parse_units(info['Vertical Units'])
        x_offset = 0.  # Not in CSV?
        y_offset = float(info['Vertical Offset'])
        x_scale = float(info['Horizontal Scale'])
        y_scale = float(info['Vertical Scale'])
        x_zero = 0.  # Not in CSV?
        y_zero = float(info['Yzero'])

        x_mag_arr = np.array(x_mag)
        y_mag_arr = np.array(y_mag)

        data_x = Q_((x_mag_arr - x_offset)*x_scale + x_zero, x_units)
        data_y = Q_((y_mag_arr - y_offset)*y_scale + y_zero, y_units)
        return data_x, data_y


try:
    from ._tektronix_async import patch_class
    patch_class(TekScope)
except (SyntaxError, ImportError):
    pass
