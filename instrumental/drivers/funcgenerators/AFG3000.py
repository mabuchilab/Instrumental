# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz
"""
Driver module for Tektronix AFG3000 Series oscilloscopes.
"""

import numpy as np
from instrumental import u, Q_
from . import FunctionGenerator

AFG3000_models = ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102',
                  'AFG3251', 'AFG3252']

_shapes = ['sinusoid', 'square', 'pulse', 'ramp', 'prnoise', 'dc', 'sinc',
           'gaussian', 'lorentz', 'erise', 'edecay', 'haversine']
_abbrev_shapes = ['sin', 'squ', 'puls', 'ramp', 'prn', 'dc', 'sinc', 'gaus',
                  'lor', 'eris', 'edec', 'hav']
_amp_keys = ['vpp', 'vrms', 'dbm']
_volt_keys = ['vpp', 'vrms', 'dbm', 'offset', 'high', 'low']

def _is_valid_shape(test_shape):
    if not test_shape:
        return False
    test_shape = test_shape.lower()
    if test_shape in _shapes or test_shape in _abbrev_shapes:
        return True
    return False

def _verify_voltage_args(kwargs):
    """
    Makes sure that at most 2 of vpp, vrms, dbm, offset, high, and low
    are set. Additionally, only 1 of vpp, vrm, and dbm can be set. Raises
    an exception if this condition is not met
    """
    if sum( (int(kwargs.has_key(k)) for k in _amp_keys) ) > 1:
        raise Exception('May include at most one of `vpp`, `vrms`, and `dbm`')

    if sum( (int(kwargs.has_key(k)) for k in _volt_keys) ) > 2:
        raise Exception('May include at most two of `vpp`, `vrms`, `dbm`, ' +
                        '`offset`, `high`, and `low`.')

def _verify_sweep_args(kwargs):
    start_stop = kwargs.has_key('start') or kwargs.has_key('stop')
    center_span = kwargs.has_key('center') or kwargs.has_key('span')
    if start_stop and center_span:
        raise Exception('May include only start/stop or center/span')


class AFG3000(FunctionGenerator):
    def __init__(self, visa_inst):
        self.inst = visa_inst

    def set_function(self, **kwargs):
        """
        Parameters
        ----------
        shape : {'SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 'DC',
        'SINC', 'GAUSsian', 'LORentz', 'ERISe', 'EDECay', 'HAVersine'}, optional
            Shape of the waveform. Case-insenitive, abbreviation or full string.
        phase : pint.Quantity or string or number, optional
            Phase of the waveform in radian-compatible units.
        vpp, vrms, dbm : pint.Quantity or string, optional
            Amplitude of the waveform in volt-compatible units.
        offset : pint.Quantity or string, optional
            Offset of the waveform in volt-compatible units.
        high : pint.Quantity or string, optional
            High level of the waveform in volt-compatible units.
        low : pint.Quantity or string, optional
            Low level of the waveform in volt-compatible units.
        channel : {1, 2}, optional
            Channel to set. Some models may have only one channel.
        """
        _verify_voltage_args(kwargs)

        channel = kwargs.get('channel', 1)

        if kwargs.has_key('vpp'):
            self.set_vpp(kwargs['vpp'], channel)
        if kwargs.has_key('vrms'):
            self.set_vrms(kwargs['vrms'], channel)
        if kwargs.has_key('dbm'):
            self.set_dbm(kwargs['dbm'], channel)
        if kwargs.has_key('offset'):
            self.set_offset(kwargs['channel'], channel)
        if kwargs.has_key('high'):
            self.set_high(kwargs['high'], channel)
        if kwargs.has_key('low'):
            self.set_low(kwargs['low'], channel)
        if kwargs.has_key('shape'):
            self.set_function_shape(kwargs['shape'], channel)
        if kwargs.has_key('phase'):
            self.set_phase(kwargs['phase'], channel)

    def set_function_shape(self, shape, channel=1):
        if not _is_valid_shape(shape):
            raise Exception("Error: invalid shape '{}'".format(shape))
        self.inst.write('source{}:function:shape {}'.format(channel, shape))

    def get_vpp(self, channel=1):
        return self._get_amplitude('vpp', channel)

    def get_vrms(self, channel=1):
        return self._get_amplitude('vrms', channel)

    def get_dbm(self, channel=1):
        return self._get_amplitude('dbm', channel)

    def _get_amplitude(self, units, channel):
        old_units = self.inst.ask('source{}:voltage:unit?'.format(channel))

        if old_units.lower() != units.lower():
            self.inst.write('source{}:voltage:unit {}'.format(channel, units))
            resp = self.inst.ask('source{}:voltage:amplitude?'.format(channel))
            self.inst.write('source{}:voltage:unit {}'.format(channel, old_units))
        else:
            # Don't need to switch units
            resp = self.inst.ask('source{}:voltage:amplitude?'.format(channel))
        return float(resp) * u.V

    def set_vpp(self, val, channel=1):
        self._set_amplitude(val, 'vpp', channel)

    def set_vrms(self, val, channel=1):
        self._set_amplitude(val, 'vrms', channel)

    def set_dbm(self, val, channel=1):
        self._set_amplitude(val, 'dbm', channel)
    
    def _set_amplitude(self, val, units, channel):
        val = Q_(val)
        mag = val.to('V').magnitude
        self.inst.write('source{}:voltage {}{}'.format(channel, mag, units))

    def set_offset(self, offset, channel=1):
        offset = Q_(offset)
        mag = offset.to('V').magnitude
        self.inst.write('source{}:voltage:offset {}V'.format(channel, mag))

    def set_high(self, high, channel=1):
        high = Q_(high)
        mag = high.to('V').magnitude
        self.inst.write('source{}:voltage:high {}V'.format(channel, mag))

    def set_low(self, low, channel=1):
        low = Q_(low)
        mag = low.to('V').magnitude
        self.inst.write('source{}:voltage:low {}V'.format(channel, mag))

    def set_phase(self, phase, channel=1):
        phase = Q_(phase) # This also accepts dimensionless numbers as rads
        if phase < -u.pi or phase > +u.pi:
            raise Exception("Phase out of range. Must be between -pi and +pi")
        mag = phase.to('rad').magnitude
        self.inst.write('source{}:phase {}rad'.format(channel, mag))

    def enable_AM(self, enable=True, channel=1):
        val = 'on' if enable else 'off'
        self.inst.write('source{}:am:state {}'.format(channel, val))

    def disable_AM(self, channel=1):
        self.inst.write('source{}:am:state off'.format(channel))

    def AM_enabled(self, channel=1):
        resp = self.inst.ask('source{}:am:state?'.format(channel))
        return bool(int(resp))

    def enable_FM(self, enable=True, channel=1):
        val = 'on' if enable else 'off'
        self.inst.write('source{}:fm:state {}'.format(channel, val))

    def disable_FM(self, channel=1):
        self.inst.write('source{}:fm:state off'.format(channel))

    def FM_enabled(self, channel=1):
        resp = self.inst.ask('source{}:fm:state?'.format(channel))
        return bool(int(resp))

    def enable_FSK(self, enable=True, channel=1):
        val = 'on' if enable else 'off'
        self.inst.write('source{}:fskey:state {}'.format(channel, val))

    def disable_FSK(self, channel=1):
        self.inst.write('source{}:fskey:state off'.format(channel))

    def FSK_enabled(self, channel=1):
        resp = self.inst.ask('source{}:fskey:state?'.format(channel))
        return bool(int(resp))

    def enable_PWM(self, enable=True, channel=1):
        val = 'on' if enable else 'off'
        self.inst.write('source{}:pwm:state {}'.format(channel, val))

    def disable_PWM(self, channel=1):
        self.inst.write('source{}:pwm:state off'.format(channel))

    def PWM_enabled(self, channel=1):
        resp = self.inst.ask('source{}:pwm:state?'.format(channel))
        return bool(int(resp))

    def enable_PM(self, enable=True, channel=1):
        val = 'on' if enable else 'off'
        self.inst.write('source{}:pm:state {}'.format(channel, val))

    def disable_PM(self, channel=1):
        self.inst.write('source{}:pm:state off'.format(channel))

    def PM_enabled(self, channel=1):
        resp = self.inst.ask('source{}:pm:state?'.format(channel))
        return bool(int(resp))

    def enable_burst(self, enable=True, channel=1):
        val = 'on' if enable else 'off'
        self.inst.write('source{}:burst:state {}'.format(channel, val))

    def disable_burst(self, channel=1):
        self.inst.write('source{}:burst:state off'.format(channel))

    def burst_enabled(self, channel=1):
        resp = self.inst.ask('source{}:burst:state?'.format(channel))
        return bool(int(resp))

    def set_frequency(self, freq, change_mode=True, channel=1):
        if change_mode:
            self.inst.write('source{}:freq:mode fixed'.format(channel))
        val = Q_(freq).to('Hz').magnitude
        self.inst.write('source{}:freq {}Hz'.format(channel, val))

    def get_frequency(self, channel=1):
        resp = self.inst.ask('source{}:freq?'.format(channel))
        return Q_(resp, 'Hz')

    def set_frequency_mode(self, mode, channel=1):
        if mode.lower() not in ['fixed', 'sweep']:
            raise Exception("Mode must be 'fixed' or 'sweep'")
        self.inst.write('source{}:freq:mode {}'.format(channel, mode))

    def get_frequency_mode(self, channel=1):
        resp = self.inst.ask('source{}:freq:mode?'.format(channel))
        return 'sweep' if 'sweep'.startswith(resp.lower()) else 'fixed'

    def sweep_enabled(self, channel=1):
        return self.get_frequency_mode(channel) == 'sweep'

    def set_sweep_start(self, start, channel=1):
        val = Q_(start).to('Hz').magnitude
        self.inst.write('source{}:freq:start {}Hz'.format(channel, val))

    def set_sweep_stop(self, stop, channel=1):
        val = Q_(stop).to('Hz').magnitude
        self.inst.write('source{}:freq:stop {}Hz'.format(channel, val))

    def set_sweep_span(self, span, channel=1):
        val = Q_(span).to('Hz').magnitude
        self.inst.write('source{}:freq:span {}Hz'.format(channel, val))

    def set_sweep_center(self, center, channel=1):
        val = Q_(center).to('Hz').magnitude
        self.inst.write('source{}:freq:center {}Hz'.format(channel, val))

    def set_sweep_time(self, time, channel=1):
        val = Q_(time).to('s').magnitude
        self.inst.write('source{}:sweep:time {}s'.format(channel, val))

    def set_sweep_hold_time(self, time, channel=1):
        val = Q_(time).to('s').magnitude
        self.inst.write('source{}:sweep:htime {}s'.format(channel, val))

    def set_sweep_return_time(self, time, channel=1):
        val = Q_(time).to('s').magnitude
        self.inst.write('source{}:sweep:rtime {}s'.format(channel, val))

    def set_sweep_spacing(self, spacing, channel=1):
        if spacing.lower() not in ['lin', 'linear', 'log', 'logarithmic']:
            raise Exception("Spacing must be 'LINear' or 'LOGarithmic'")
        self.inst.write('source{}:sweep:spacing {}'.format(channel, spacing))

    def set_sweep(self, channel=1, **kwargs):
        _verify_sweep_args(kwargs)
        if kwargs.has_key('start'):
            self.set_sweep_start(kwargs['start'], channel)
        if kwargs.has_key('stop'):
            self.set_sweep_stop(kwargs['stop'], channel)
        if kwargs.has_key('span'):
            self.set_sweep_span(kwargs['span'], channel)
        if kwargs.has_key('center'):
            self.set_sweep_center(kwargs['center'], channel)
        if kwargs.has_key('sweep_time'):
            self.set_sweep_time(kwargs['sweep_time'], channel)
        if kwargs.has_key('hold_time'):
            self.set_sweep_hold_time(kwargs['hold_time'], channel)
        if kwargs.has_key('return_time'):
            self.set_sweep_return_time(kwargs['return_time'], channel)
        if kwargs.has_key('spacing'):
            self.set_sweep_spacing(kwargs['spacing'], channel)

    def set_am_depth(self, depth, channel=1):
        val = Q_(depth).magnitude
        self.inst.write('source{}:am:depth {:.8f}pct'.format(channel, val))

    def set_arb_func(self, data, interp=None, num_pts=10000):
        """ Write arbitrary waveform data to EditMemory.

        Parameters
        ----------
        data : array_like
            A 1D array of real values to be used as evenly-spaced points. The
            values will be normalized to extend from 0 t0 16382. It must have
            a length in the range [2, 131072]
        interp : str or int, optional
            Interpolation to use for smoothing out data. None indicates no
            interpolation. Values include ('linear', 'nearest', 'zero',
            'slinear', 'quadratic', 'cubic'), or an int to specify the order of
            spline interpolation. See scipy.interpolate.interp1d for details.
        num_pts : int
            Number of points to use in interpolation. Default is 10000. Must
            be greater than or equal to the number of points in `data`, and at
            most 131072.
        """
        data = np.asanyarray(data)
        if data.ndim != 1:
            raise Exception("`data` must be convertible to a 1-dimensional array")
        if not ( 2 <= len(data) <= 131072 ):
            raise Exception("`data` must contain between 2 and 131072 points")

        # Handle interpolation
        if interp is not None:
            from scipy.interpolate import interp1d

            if not (len(data) <= num_pts <= 131072):
                raise Exception("`num_pts` must contain between " +
                                "`len(data)` and 131072 points")
            x = np.linspace(0, num_pts-1, len(data))
            func = interp1d(x, data, kind=interp)
            data = func(np.linspace(0, num_pts-1, num_pts))

        # Normalize data to between 0 and 16,382
        min = data.min()
        max = data.max()
        data = (data-min)*(16382/(max-min))
        data = data.astype('>u2') # Convert to big-endian 16-bit unsigned int

        bytes = data.tostring()
        num = len(bytes)
        bytes = b"#{}{}".format(len(str(num)), num) + bytes
        self.inst.write_raw(b'data ememory,' + bytes)

    def get_ememory(self):
        self.inst.write('data? ememory')
        resp = self.inst.read_raw()
        if resp[0] != b'#':
            raise Exception("Binary reponse missing header! Something's wrong.")
        header_width = int(resp[1]) + 2
        num_bytes = int(resp[2:header_width])
        data = np.frombuffer(resp, dtype='>u2', offset=header_width, count=int(num_bytes/2))
        return data

