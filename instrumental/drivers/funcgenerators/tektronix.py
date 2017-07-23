# -*- coding: utf-8 -*-
# Copyright 2014-2017 Nate Bogdanowicz
"""
Driver module for Tektronix function generators. Currently supports:

* AFG 3000 series
"""
import numpy as np
from . import FunctionGenerator
from ... import u, Q_

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'AFG_3000': ('TEKTRONIX',
                 ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102', 'AFG3251', 'AFG3252'])
}

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
    if sum( (int(k in kwargs) for k in _amp_keys) ) > 1:
        raise Exception('May include at most one of `vpp`, `vrms`, and `dbm`')

    if sum( (int(k in kwargs) for k in _volt_keys) ) > 2:
        raise Exception('May include at most two of `vpp`, `vrms`, `dbm`, ' +
                        '`offset`, `high`, and `low`.')


def _verify_sweep_args(kwargs):
    start_stop = ('start' in kwargs) or ('stop' in kwargs)
    center_span = ('center' in kwargs) or ('span' in kwargs)
    if start_stop and center_span:
        raise Exception('May include only start/stop or center/span')


class AFG_3000(FunctionGenerator):
    def set_function(self, **kwargs):
        """
        Set selected function parameters. Useful for setting multiple
        parameters at once. See individual setters for more details.

        When setting the waveform amplitude, you may use up to two of `high`,
        `low`, `offset`, and `vpp`/`vrms`/`dbm`.

        Parameters
        ----------
        shape : {'SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 'DC', \
        'SINC', 'GAUSsian', 'LORentz', 'ERISe', 'EDECay', 'HAVersine',
        'USER1', 'USER2', 'USER3', 'USER4', 'EMEMory'}, optional
            Shape of the waveform. Case-insenitive, abbreviation or full
            string.
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
            Output channel to modify. Some models may have only one channel.
        """
        _verify_voltage_args(kwargs)

        channel = kwargs.get('channel', 1)

        if 'vpp' in kwargs:
            self.set_vpp(kwargs['vpp'], channel)
        if 'vrms' in kwargs:
            self.set_vrms(kwargs['vrms'], channel)
        if 'dbm' in kwargs:
            self.set_dbm(kwargs['dbm'], channel)
        if 'offset' in kwargs:
            self.set_offset(kwargs['channel'], channel)
        if 'high' in kwargs:
            self.set_high(kwargs['high'], channel)
        if 'low' in kwargs:
            self.set_low(kwargs['low'], channel)
        if 'shape' in kwargs:
            self.set_function_shape(kwargs['shape'], channel)
        if 'phase' in kwargs:
            self.set_phase(kwargs['phase'], channel)

    def set_function_shape(self, shape, channel=1):
        """ Set shape of output function.

        Parameters
        ----------
        shape : {'SINusoid', 'SQUare', 'PULSe', 'RAMP', 'PRNoise', 'DC', \
        'SINC', 'GAUSsian', 'LORentz', 'ERISe', 'EDECay', 'HAVersine', 'USER1', \
        'USER2', 'USER3', 'USER4', 'EMEMory'}, optional
            Shape of the waveform. Case-insenitive string that contains a valid
            shape or its abbreviation. The abbreviations are indicated above by
            capitalization.  For example, `sin`, `SINUSOID`, and `SiN` are all
            valid inputs, while `sinus` is not.
        channel : {1, 2}, optional
            Output channel to modify. Some models may have only one channel.
        """
        if not _is_valid_shape(shape):
            raise Exception("Error: invalid shape '{}'".format(shape))
        self._rsrc.write('source{}:function:shape {}'.format(channel, shape))

    def get_vpp(self, channel=1):
        """ Get the peak-to-peak voltage of the current waveform.

        Returns
        -------
        vpp : pint.Quantity
            The current waveform's peak-to-peak voltage
        """
        return self._get_amplitude('vpp', channel)

    def get_vrms(self, channel=1):
        """ Get the RMS voltage of the current waveform.

        Returns
        -------
        vrms : pint.Quantity
            The current waveform's RMS voltage
        """
        return self._get_amplitude('vrms', channel)

    def get_dbm(self, channel=1):
        """ Get the amplitude of the current waveform in dBm.

        Note that this returns a float, not a pint.Quantity

        Returns
        -------
        dbm : float
            The current waveform's dBm amplitude
        """
        return self._get_amplitude('dbm', channel)

    def _get_amplitude(self, units, channel):
        old_units = self._rsrc.query('source{}:voltage:unit?'.format(channel))

        if old_units.lower() != units.lower():
            self._rsrc.write('source{}:voltage:unit {}'.format(channel, units))
            resp = self._rsrc.query('source{}:voltage:amplitude?'.format(channel))
            self._rsrc.write('source{}:voltage:unit {}'.format(channel, old_units))
        else:
            # Don't need to switch units
            resp = self._rsrc.query('source{}:voltage:amplitude?'.format(channel))
        return float(resp) * u.V

    def set_vpp(self, vpp, channel=1):
        """ Set the peak-to-peak voltage of the current waveform.

        Parameters
        ----------
        vpp : pint.Quantity
            The new peak-to-peak voltage
        """
        self._set_amplitude(vpp, 'vpp', channel)

    def set_vrms(self, vrms, channel=1):
        """ Set the amplitude of the current waveform in dBm.

        Parameters
        ----------
        vrms : pint.Quantity
            The new RMS voltage
        """
        self._set_amplitude(vrms, 'vrms', channel)

    def set_dbm(self, dbm, channel=1):
        """ Set the amplitude of the current waveform in dBm.

        Note that this returns a float, not a pint.Quantity

        Parameters
        ----------
        dbm : float
            The current waveform's dBm amplitude
        """
        self._set_amplitude(dbm, 'dbm', channel)

    def _set_amplitude(self, val, units, channel):
        val = Q_(val)
        mag = val.to('V').magnitude
        self._rsrc.write('source{}:voltage {}{}'.format(channel, mag, units))

    def set_offset(self, offset, channel=1):
        """ Set the voltage offset of the current waveform.

        This changes the offset while keeping the amplitude fixed.

        Parameters
        ----------
        offset : pint.Quantity
            The new voltage offset in volt-compatible units
        """
        offset = Q_(offset)
        mag = offset.to('V').magnitude
        self._rsrc.write('source{}:voltage:offset {}V'.format(channel, mag))

    def set_high(self, high, channel=1):
        """ Set the high voltage level of the current waveform.

        This changes the high level while keeping the low level fixed.

        Parameters
        ----------
        high : pint.Quantity
            The new high level in volt-compatible units
        """
        high = Q_(high)
        mag = high.to('V').magnitude
        self._rsrc.write('source{}:voltage:high {}V'.format(channel, mag))

    def set_low(self, low, channel=1):
        """ Set the low voltage level of the current waveform.

        This changes the low level while keeping the high level fixed.

        Parameters
        ----------
        low : pint.Quantity
            The new low level in volt-compatible units
        """
        low = Q_(low)
        mag = low.to('V').magnitude
        self._rsrc.write('source{}:voltage:low {}V'.format(channel, mag))

    def set_phase(self, phase, channel=1):
        """ Set the phase offset of the current waveform.

        Parameters
        ----------
        phase : pint.Quantity or number
            The new low level in radian-compatible units. Unitless numbers are
            treated as radians.
        """
        phase = Q_(phase)  # This also accepts dimensionless numbers as rads
        if phase < -u.pi or phase > +u.pi:
            raise Exception("Phase out of range. Must be between -pi and +pi")
        mag = phase.to('rad').magnitude
        self._rsrc.write('source{}:phase {}rad'.format(channel, mag))

    def enable_AM(self, enable=True, channel=1):
        """ Enable amplitude modulation mode.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable or disable AM
        """
        val = 'on' if enable else 'off'
        self._rsrc.write('source{}:am:state {}'.format(channel, val))

    def disable_AM(self, channel=1):
        """ Disable amplitude modulation mode. """
        self._rsrc.write('source{}:am:state off'.format(channel))

    def AM_enabled(self, channel=1):
        """ Returns whether amplitude modulation is enabled.

        Returns
        -------
        bool
            Whether AM is enabled.
        """
        resp = self._rsrc.query('source{}:am:state?'.format(channel))
        return bool(int(resp))

    def enable_FM(self, enable=True, channel=1):
        """ Enable frequency modulation mode.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable or disable FM
        """
        val = 'on' if enable else 'off'
        self._rsrc.write('source{}:fm:state {}'.format(channel, val))

    def disable_FM(self, channel=1):
        """ Disable frequency modulation mode. """
        self._rsrc.write('source{}:fm:state off'.format(channel))

    def FM_enabled(self, channel=1):
        """ Returns whether frequency modulation is enabled.

        Returns
        -------
        bool
            Whether FM is enabled.
        """
        resp = self._rsrc.query('source{}:fm:state?'.format(channel))
        return bool(int(resp))

    def enable_FSK(self, enable=True, channel=1):
        """ Enable frequency-shift keying mode.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable or disable FSK
        """
        val = 'on' if enable else 'off'
        self._rsrc.write('source{}:fskey:state {}'.format(channel, val))

    def disable_FSK(self, channel=1):
        """ Disable frequency-shift keying mode. """
        self._rsrc.write('source{}:fskey:state off'.format(channel))

    def FSK_enabled(self, channel=1):
        """ Returns whether frequency-shift keying modulation is enabled.

        Returns
        -------
        bool
            Whether FSK is enabled.
        """
        resp = self._rsrc.query('source{}:fskey:state?'.format(channel))
        return bool(int(resp))

    def enable_PWM(self, enable=True, channel=1):
        """ Enable pulse width modulation mode.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable or disable PWM
        """
        val = 'on' if enable else 'off'
        self._rsrc.write('source{}:pwm:state {}'.format(channel, val))

    def disable_PWM(self, channel=1):
        """ Disable pulse width modulation mode. """
        self._rsrc.write('source{}:pwm:state off'.format(channel))

    def PWM_enabled(self, channel=1):
        """ Returns whether pulse width modulation is enabled.

        Returns
        -------
        bool
            Whether PWM is enabled.
        """
        resp = self._rsrc.query('source{}:pwm:state?'.format(channel))
        return bool(int(resp))

    def enable_PM(self, enable=True, channel=1):
        """ Enable phase modulation mode.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable or disable PM
        """
        val = 'on' if enable else 'off'
        self._rsrc.write('source{}:pm:state {}'.format(channel, val))

    def disable_PM(self, channel=1):
        """ Disable phase modulation mode. """
        self._rsrc.write('source{}:pm:state off'.format(channel))

    def PM_enabled(self, channel=1):
        """ Returns whether phase modulation is enabled.

        Returns
        -------
        bool
            Whether PM is enabled.
        """
        resp = self._rsrc.query('source{}:pm:state?'.format(channel))
        return bool(int(resp))

    def enable_burst(self, enable=True, channel=1):
        """ Enable burst mode.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable or disable burst mode.
        """
        val = 'on' if enable else 'off'
        self._rsrc.write('source{}:burst:state {}'.format(channel, val))

    def disable_burst(self, channel=1):
        """ Disable burst mode. """
        self._rsrc.write('source{}:burst:state off'.format(channel))

    def burst_enabled(self, channel=1):
        """ Returns whether burst mode is enabled.

        Returns
        -------
        bool
            Whether burst mode is enabled.
        """
        resp = self._rsrc.query('source{}:burst:state?'.format(channel))
        return bool(int(resp))

    def set_frequency(self, freq, change_mode=True, channel=1):
        """ Set the frequency to be used in fixed frequency mode.

        Parameters
        ----------
        freq : pint.Quantity
            The frequency to be used in fixed frequency mode.
        change_mode : bool, optional
            If True, will set the frequency mode to `fixed`.
        """
        if change_mode:
            self._rsrc.write('source{}:freq:mode fixed'.format(channel))
        val = Q_(freq).to('Hz').magnitude
        self._rsrc.write('source{}:freq {}Hz'.format(channel, val))

    def get_frequency(self, channel=1):
        """ Get the frequency to be used in fixed frequency mode. """
        resp = self._rsrc.query('source{}:freq?'.format(channel))
        return Q_(resp, 'Hz')

    def set_frequency_mode(self, mode, channel=1):
        """ Set the frequency mode.

        In fixed mode, the waveform's frequency is kept constant. In sweep mode,
        it is swept according to the sweep settings.

        Parameters
        ----------
        mode : {'fixed', 'sweep'}
            Mode to switch to.
        """
        if mode.lower() not in ['fixed', 'sweep']:
            raise Exception("Mode must be 'fixed' or 'sweep'")
        self._rsrc.write('source{}:freq:mode {}'.format(channel, mode))

    def get_frequency_mode(self, channel=1):
        """ Get the frequency mode.

        Returns
        -------
        'fixed' or 'sweep'
            The frequency mode
        """
        resp = self._rsrc.query('source{}:freq:mode?'.format(channel))
        return 'sweep' if 'sweep'.startswith(resp.lower()) else 'fixed'

    def sweep_enabled(self, channel=1):
        """ Whether the frequency mode is sweep.

        Just a convenience method to avoid writing
        ``get_frequency_mode() == 'sweep'``.

        Returns
        -------
        bool
            Whether the frequency mode is sweep
        """
        return self.get_frequency_mode(channel) == 'sweep'

    def set_sweep_start(self, start, channel=1):
        """ Set the sweep start frequency.

        This sets the start frequency while keeping the stop frequency
        fixed. The span and center frequencies will be changed.

        Parameters
        ----------
        start : pint.Quantity
            The start frequency of the sweep in Hz-compatible units
        """
        val = Q_(start).to('Hz').magnitude
        self._rsrc.write('source{}:freq:start {}Hz'.format(channel, val))

    def set_sweep_stop(self, stop, channel=1):
        """ Set the sweep stop frequency.

        This sets the stop frequency while keeping the start frequency
        fixed. The span and center frequencies will be changed.

        Parameters
        ----------
        stop : pint.Quantity
            The stop frequency of the sweep in Hz-compatible units
        """
        val = Q_(stop).to('Hz').magnitude
        self._rsrc.write('source{}:freq:stop {}Hz'.format(channel, val))

    def set_sweep_span(self, span, channel=1):
        """ Set the sweep frequency span.

        This sets the sweep frequency span while keeping the center frequency
        fixed. The start and stop frequencies will be changed.

        Parameters
        ----------
        span : pint.Quantity
            The frequency span of the sweep in Hz-compatible units
        """
        val = Q_(span).to('Hz').magnitude
        self._rsrc.write('source{}:freq:span {}Hz'.format(channel, val))

    def set_sweep_center(self, center, channel=1):
        """ Set the sweep frequency center.

        This sets the sweep center frequency while keeping the sweep frequency
        span fixed. The start and stop frequencies will be changed.

        Parameters
        ----------
        center : pint.Quantity
            The center frequency of the sweep in Hz-compatible units
        """
        val = Q_(center).to('Hz').magnitude
        self._rsrc.write('source{}:freq:center {}Hz'.format(channel, val))

    def set_sweep_time(self, time, channel=1):
        """ Set the sweep time.

        The sweep time does not include hold time or return time. Sweep time
        must be between 1 ms and 300 s.

        Parameters
        ----------
        time : pint.Quantity
            The sweep time in second-compatible units. Must be between 1 ms and
            200 s
        """
        val = Q_(time).to('s').magnitude
        if not (1e-3 <= val <= 200):
            raise Exception("Sweep time must be between 1 ms and 200 s")
        self._rsrc.write('source{}:sweep:time {}s'.format(channel, val))

    def set_sweep_hold_time(self, time, channel=1):
        """ Set the hold time of the sweep.

        The hold time is the amount of time that the frequency is held constant
        after reaching the stop frequency.

        Parameters
        ----------
        time : pint.Quantity
            The hold time in second-compatible units
        """
        val = Q_(time).to('s').magnitude
        self._rsrc.write('source{}:sweep:htime {}s'.format(channel, val))

    def set_sweep_return_time(self, time, channel=1):
        """ Set the return time of the sweep.

        The return time is the amount of time that the frequency spends
        sweeping from the stop frequency back to the start frequency. This
        does not include hold time.

        Parameters
        ----------
        time : pint.Quantity
            The return time in second-compatible units
        """
        val = Q_(time).to('s').magnitude
        self._rsrc.write('source{}:sweep:rtime {}s'.format(channel, val))

    def set_sweep_spacing(self, spacing, channel=1):
        """ Set whether a sweep is linear or logarithmic.

        Parameters
        ----------
        spacing : {'linear', 'lin', 'logarithmic', 'log'}
            The spacing in time of the sweep frequencies
        """
        if spacing.lower() not in ['lin', 'linear', 'log', 'logarithmic']:
            raise Exception("Spacing must be 'LINear' or 'LOGarithmic'")
        self._rsrc.write('source{}:sweep:spacing {}'.format(channel, spacing))

    def set_sweep(self, channel=1, **kwargs):
        """ Set selected sweep parameters.

        Automatically enables sweep mode.

        Parameters
        ----------
        start : pint.Quantity
            The start frequency of the sweep in Hz-compatible units
        stop : pint.Quantity
            The stop frequency of the sweep in Hz-compatible units
        span : pint.Quantity
            The frequency span of the sweep in Hz-compatible units
        center : pint.Quantity
            The center frequency of the sweep in Hz-compatible units
        sweep_time : pint.Quantity
            The sweep time in second-compatible units. Must be between 1 ms and
            300 s
        hold_time : pint.Quantity
            The hold time in second-compatible units
        return_time : pint.Quantity
            The return time in second-compatible units
        spacing : {'linear', 'lin', 'logarithmic', 'log'}
            The spacing in time of the sweep frequencies
        """
        _verify_sweep_args(kwargs)
        self.set_frequency_mode('sweep')

        if 'start' in kwargs:
            self.set_sweep_start(kwargs['start'], channel)
        if 'stop' in kwargs:
            self.set_sweep_stop(kwargs['stop'], channel)
        if 'span' in kwargs:
            self.set_sweep_span(kwargs['span'], channel)
        if 'center' in kwargs:
            self.set_sweep_center(kwargs['center'], channel)
        if 'sweep_time' in kwargs:
            self.set_sweep_time(kwargs['sweep_time'], channel)
        if 'hold_time' in kwargs:
            self.set_sweep_hold_time(kwargs['hold_time'], channel)
        if 'return_time' in kwargs:
            self.set_sweep_return_time(kwargs['return_time'], channel)
        if 'spacing' in kwargs:
            self.set_sweep_spacing(kwargs['spacing'], channel)

    def set_am_depth(self, depth, channel=1):
        """ Set depth of amplitude modulation.

        Parameters
        ----------
        depth : number
            Depth of modulation in percent. Must be between 0.0% and 120.0%.
            Has resolution of 0.1%.
        """
        val = Q_(depth).magnitude
        if not (0.0 <= val <= 120.0):
            raise Exception("Depth must be between 0.0 and 120.0")
        self._rsrc.write('source{}:am:depth {:.1f}pct'.format(channel, val))

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
        data = data.astype('>u2')  # Convert to big-endian 16-bit unsigned int

        bytes = data.tostring()
        num = len(bytes)
        bytes = b"#{}{}".format(len(str(num)), num) + bytes
        self._rsrc.write_raw(b'data ememory,' + bytes)

    def get_ememory(self):
        """ Get array of data from edit memory.

        Returns
        -------
        numpy.array
            Data retrieved from the AFG's edit memory.
        """
        self._rsrc.write('data? ememory')
        resp = self._rsrc.read_raw()
        if resp[0] != b'#':
            raise Exception("Binary reponse missing header! Something's wrong.")
        header_width = int(resp[1]) + 2
        num_bytes = int(resp[2:header_width])
        data = np.frombuffer(resp, dtype='>u2', offset=header_width, count=int(num_bytes/2))
        return data
