# -*- coding: utf-8  -*-
"""
Driver for the Santec TSL-550 Tunable Laser.
Copyright 2018-2019 Sequoia Ploeg and Alec Hammond

The Santec TSL-550 drivers, which among
other things make the usb connection appear as a serial port, must be
installed.


Warning
-------
An unidentifiable bug results in the return value of many functions being the setting of the laser
BEFORE the update instead of the commanded setting. To verify some value has been set to 
the commanded value, call its respective a second time without any arguments.
"""
from __future__ import division
import sys
import time
import struct
import pyvisa as visa

from instrumental.drivers.lasers import Laser
from instrumental.drivers import VisaMixin, ParamSet
from instrumental import Q_

_INST_PARAMS_ = ['visa_address']
_INST_VISA_INFO_ = {
    'TSL550': ('SANTEC', ['TSL-550']),
}

def list_instruments():
    """Get a list of all Santec TSL-550 lasers currently attached."""
    paramsets = []
    search_string = "ASRL?*"
    rm = visa.ResourceManager()
    raw_spec_list = rm.list_resources(search_string)

    for spec in raw_spec_list:
        try:
            inst = rm.open_resource(spec, read_termination='\r', write_termination='\r')
            idn = inst.query("*IDN?")
            manufacturer, model, serial, version = idn.rstrip().split(',', 4)
            if 'TSL-550' in model:
                paramsets.append(ParamSet(TSL550, visa_address=spec, manufacturer=manufacturer, serial=serial, model=model, version=version))
        except visa.errors.VisaIOError as vio:
            # Ignore unknown serial devices
            pass

    return paramsets

class TSL550(Laser, VisaMixin):
    """ A Santec TSL-550 laser.

    Lasers can only be accessed by their serial port address.
    """

    # continuous, two-way, external trigger, constant frequency interval
    SWEEP_MODE_MAP = {
        (True, False, False, False): 1,
        (True, True, False, False): 2,
        (False, False, False, False): 3,
        (False, True, False, False): 4,
        (False, False, False, True): 5,
        (False, True, False, True): 6,
        (True, False, True, False): 7,
        (True, True, True, False): 8,
        (False, False, True, False): 9,
        (False, True, True, False): 10,
        (False, False, True, True): 11,
        (False, True, True, True): 12
    }
    SWEEP_MODE_MAP_REV = {num: settings for settings, num in SWEEP_MODE_MAP.items()}

    # Sweep mode statuses
    SWEEP_OFF = 0
    SWEEP_RUNNING = 1
    SWEEP_PAUSED = 2
    SWEEP_TRIGGER_WAIT = 3
    SWEEP_JUMP = 4

    MINIMUM_WAVELENGTH = 1500
    MAXIMUM_WAVELENGTH = 1630

    def _initialize(self):
        """
        Connect to the TSL550. Address is the serial port, baudrate
        can be set on the device.

        Address will change based on specific connection settings.
        """
        # TODO: Maybe; if the termination isn't working for Py3, try encoding it.
        # if sys.version_info.major >= 3: # Python 3 compatibility: convert to bytes
        #     terminator = terminator.encode("ASCII")
        # self.terminator = terminator

        self.resource.write_termination = '\r'
        self.resource.read_termination = '\r'
        self.resource.baud_rate = 9600
        self.resource.timeout = 100
        self.resource.query_delay = 0.05
        self.resource.flush(visa.constants.VI_READ_BUF_DISCARD)
        self.resource.flush(visa.constants.VI_WRITE_BUF_DISCARD)

        # Make sure the shutter is on
        self.query("SU")
        shutter = self.close_shutter()

        # Set power management to auto
        self.power_control = "auto"
        self.power_auto()

        # Set sweep mode to continuous, two-way, trigger off
        self.sweep_set_mode()

    def close(self):
        pass

    def _set_var(self, name, precision, val):
        """
        Generic function to set a floating-point variable on the
        laser, or return the current value.
        """

        if val is not None:
            command = ("{}{:."+str(precision)+"f}").format(name, val)
        else:
            command = name

        # # Convert to bytes (Python 3 compatibility)
        # if sys.version_info.major >= 3:
        #     command = command.encode("ASCII")

        response = self.query(command)
        return response

    def ident(self):
        """
        Query the device to identify itself.

        Returns
        -------
        str
            SANTEC,TSL-550,########,****.****
            # field = serial number of the device
            * field = firmware version

        >>> laser.ident()
        'SANTEC,TSL-550,06020001,0001.0000'
        """

        return self.query('*IDN?')

    def on(self):
        """
        Turns on the laser diode.
        """

        self.is_on = True
        self.query("LO")

    def off(self):
        """
        Turns off the laser diode.
        """

        self.is_on = False
        self.query("LF")

    def wavelength(self, val=None):
        """
        Sets the output wavelength. If a value is not specified, returns the currently set wavelength.

        Parameters
        ----------
        val : float, optional
            The wavelength the laser will be set to in nanometers.
            Step: 0.0001 (nm)

        Returns
        -------
        Quantity
            The currently set wavelength in nanometers, and its units.

        You can get the current wavelength by calling without arguments.

        >>> laser.wavelength()
        <Quantity(1630.0, 'nanometer')>

        The following sets the output wavelength to 1560.123 nanometers.

        >>> laser.wavelength(1560.123)
        <Quantity(1630.0, 'nanometer')> # Bug returns the last set wavelength
        """

        return Q_(float(self._set_var("WA", 4, val)), 'nm')

    def frequency(self, val=None):
        """
        Tune the laser to a new frequency. If a value is not
        specified, returns the currently set frequency.

        Parameters
        ----------
        val : float, optional
            The frequency to set the laser to in terahertz.
            Step: 0.00001 (THz)

        Returns
        -------
        Quantity
            The currently set frequency in terahertz, and its units.

        >>> laser.frequency()
        <Quantity(183.92175, 'terahertz')>
        >>> laser.frequency(192.0000)
        <Quantity(183.92175, 'terahertz')> # Bug returns the last set frequency
        """

        return Q_(float(self._set_var("FQ", 5, val)), 'THz')

    def power_mW(self, val=None):
        """
        Set the output optical power in milliwatts. If a value is not
        specified, return the current output power.

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in milliwatts.
            Range: 0.02 - 20 (mW, typical)
            Minimum step: 0.01 (mW)

        Returns
        -------
        Quantity
            The currently set power in milliwatts, with its units.

        >>> laser.power_mW()
        <Quantity(2e-05, 'milliwatt')>
        >>> laser.power_mW(10)
        <Quantity(2e-05, 'milliwatt')> # Bug returns the last set power
        """

        return Q_(float(self._set_var("LP", 2, val)), 'mW')

    def power_dBm(self, val=None):
        """
        Set the output optical power in decibel-milliwatts (dBm). If a value
        is not specified, returns the current power.

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in decibel-milliwatts.
            Range: -17 to +13 (dBm, typical)
            Minimum step: 0.01 (dB)

        Returns
        -------
        float
            The currently set power in decibel-milliwatts.

        You can get the current power by calling without arguments.
        The below code indicates the currently output power is -40 dBm.

        >>> laser.power_dBm()
        -040.000

        The following sets the output optical power to +3 dBm.

        >>> laser.power_dBm(3)
        -040.000 # Bug returns the last set power
        """

        return float(self._set_var("OP", 2, val))

    def power_auto(self):
        """
        Turn on automatic power control.
        """

        self.power_control = "auto"
        self.query("AF")

    def power_manual(self):
        """
        Turn on manual power control.
        """

        self.power_control = "manual"
        self.query("AO")

    def sweep_wavelength(self, start, stop, duration, number=1,
                         delay=0, continuous=True, step_size=1,
                         twoway=False, trigger=False):
        r"""
        Conduct a sweep between two wavelengths. This method goes from
        the start wavelength to the stop wavelength (units:
        manometres). The sweep is then repeated the number of times
        set in the number parameter.
        If delay (units: seconds) is specified, there is a pause of
        that duration between each sweep.
        If the parameter continuous is False, then the sweep will be
        conducted in steps of fixed size as set by the step_size
        parameter (units: nanometres).
        In continuous mode, the duration is interpreted as the time
        for one sweep. In stepwise mode, it is used as the dwell time
        for each step. In both cases it has units of seconds and
        should be specified in 100 microsecond intervals.
        If the twoway parameter is True then one sweep is considered
        to be going from the start wavelength to the stop wavelength
        and then back to the start; if it is False then one sweep
        consists only of going from the start to the top, and the
        laser will simply jump back to the start wavelength at the
        start of the next sweep.
        If the trigger parameter is False then the sweep will execute
        immediately. If it is true, the laser will wait for an
        external trigger before starting.
        To illustrate the different sweep modes:
            Continuous, one-way    Continuous, two-way
                /   /                  /\    /\      <-- stop frequency
               /   /                  /  \  /  \
              /   /                  /    \/    \    <-- start frequency
              <-> duration           <----> duration
            Stepwise, one-way      Stepwise, two-way
                    __|      __|              _||_        _||_      <-- stop frequency
                 __|      __|               _|    |_    _|    |_ } step size
              __|      __|               _|        |__|        |_  <-- start frequency
              <-> duration               <> duration
            Continuous, one-way, delay    Continuous, two-way, delay
                /     /                       /\       /\
               /     /                       /  \     /  \
              /  ___/                       /    \___/    \
                 <-> delay                        <-> delay
        """

        # Set start and end wavelengths
        self.sweep_start_wavelength(start)
        self.sweep_end_wavelength(stop)

        # Set timing
        self.sweep_delay(delay)
        if continuous: # Calculate speed
            speed = abs(stop - start) / duration

            if twoway: # Need to go twice as fast to go up then down in the same time
                speed *= 2

            self.sweep_speed(speed)
        else: # Interpret as time per step
            self.sweep_step_time(duration)

        self.sweep_set_mode(continuous=continuous, twoway=twoway,
                            trigger=trigger, const_freq_step=False)

        if not self.is_on: # Make sure the laser is on
            self.on()

        self.sweep_start(number)

    def sweep_frequency(self, start, stop, duration, number=1,
                        delay=0, continuous=True, step_size=1,
                        twoway=False, trigger=False):
        r"""
        Conduct a sweep between two frequencies. This method goes from
        the start frequency to the stop frequency (units: terahertz).
        The sweep is then repeated the number of times set in the
        number parameter.
        If delay (units: seconds) is specified, there is a pause of
        that duration between each sweep.
        If the parameter continuous is False, then the sweep will be
        conducted in steps of fixed size as set by the step_size
        parameter (units: terahertz).
        In continuous mode, the duration is interpreted as the time
        for one sweep. In stepwise mode, it is used as the dwell time
        for each step. In both cases it has units of seconds and
        should be specified in 100 microsecond intervals.
        If the twoway parameter is True then one sweep is considered
        to be going from the start frequency to the stop frequency and
        then back to the start; if it is False then one sweep consists
        only of going from the start to the top, and the laser will
        simply jump back to the start frequency at the start of the
        next sweep.
        If the trigger parameter is False then the sweep will execute
        immediately. If it is true, the laser will wait for an
        external trigger before starting.
        To illustrate the different sweep modes:
            Continuous, one-way    Continuous, two-way
                /   /                  /\    /\      <-- stop frequency
               /   /                  /  \  /  \
              /   /                  /    \/    \    <-- start frequency
              <-> duration           <----> duration
            Stepwise, one-way      Stepwise, two-way
                    __|      __|              _||_        _||_      <-- stop frequency
                 __|      __|               _|    |_    _|    |_ } step size
              __|      __|               _|        |__|        |_  <-- start frequency
              <-> duration               <> duration
            Continuous, one-way, delay    Continuous, two-way, delay
                /     /                       /\       /\
               /     /                       /  \     /  \
              /  ___/                       /    \___/    \
                 <-> delay                        <-> delay
        """

        # Set start and end frequencies
        self.sweep_start_frequency(start)
        self.sweep_end_frequency(stop)

        # Set timing
        self.sweep_delay(delay)
        if continuous: # Calculate speed
            speed = abs(3e8/stop - 3e8/start) / duration # Convert to wavelength

            if twoway: # Need to go twice as fast to go up then down in the same time
                speed *= 2

            self.sweep_speed(speed)
        else: # Interpret as time per step
            self.sweep_step_time(duration)

        self.sweep_set_mode(continuous=continuous, twoway=twoway,
                            trigger=trigger, const_freq_step=not continuous)

        if not self.is_on: # Make sure the laser is on
            self.on()

        self.sweep_start(number)

    def sweep_start(self, num=1):
        """
        Sweep between two wavelengths one or more times. Set the start
        and end wavelengths with
        sweep_(start|end)_(wavelength|frequency), and the sweep
        operation mode with sweep_set_mode.

        Parameters
        ----------
        num : int, optional
            The number of times to perform the sweep (default is 1).
        """

        self.query("SZ{:d}".format(num)) # Set number of sweeps
        self.query("SG") # Start sweeping

    def sweep_pause(self):
        """
        Pause the sweep.  When a fast sweep speed is set, pause will 
        not function. Use `sweep_resume()` to resume.
        """

        self.query("SP")

    def sweep_resume(self):
        """
        Resume a paused sweep.
        """

        self.query("SR")

    def sweep_stop(self, immediate=True):
        """
        Prematurely quit a sweep. 
        
        If the parameter immediate is True,
        the sweep will stop at once. If the parameter is False and the
        sweep is continuous, the sweep will stop once if finishes the
        current sweep.

        Parameters
        ----------
        immediate : bool
            If true, the sweep will stop at once. If false and the
            sweep is continuous, the sweep will stop once it reaches
            the end wavelength of its current sweep (the default is `True`).
        """

        if immediate:
            self.sweep_pause()

        self.query("SQ")

    def sweep_status(self):
        """
        Gets the current condition of the sweeping function. 
        
        Returns
        -------
        status : int
            The status code correspond to the following:
            0: Stop (`TSL550.SWEEP_OFF`)
            1: Executing (`TSL550.SWEEP_RUNNING`)
            2: Pause (`TSL550.SWEEP_PAUSED`)
            3: Awaiting Trigger (`TSL550.SWEEP_TRIGGER_WAIT`)
                This means that the sweep has been set to start on 
                an external trigger and that trigger has not yet 
                been received.
            4: Setting to sweep start wavelength (`TSL550.SWEEP_JUMP`)
                This means that the laser is transitioning between 
                the end of one sweep and the start of the next in 
                one-way sweep mode.

        >>> laser.sweep_status()
        0
        >>> laser.sweep_status() == laser.SWEEP_OFF
        True
        """

        return int(self.query("SK"))

    def sweep_set_mode(self, continuous=True, twoway=True, trigger=False, const_freq_step=False):
        r"""
        Set the mode of the sweep. Options:
        - Continuous or stepwise:
                /        _|
               /  vs   _|
              /      _|
        - Two-way:
                /\        /   /
               /  \  vs  /   /
              /    \    /   /
        - Constant frequency interval (requires stepwise mode)
        - Start from external trigger
        """

        try:
            mode = TSL550.SWEEP_MODE_MAP[(continuous, twoway, trigger, const_freq_step)]
        except KeyError:
            raise AttributeError("Invalid sweep configuration.")

        self.query("SM{}".format(mode))

    def sweep_get_mode(self):
        """
        Return the current sweep configuration as a dictionary. See
        sweep_set_mode for what the parameters mean.
        """

        mode_num = int(self.query("SM"))
        mode_settings = TSL550.SWEEP_MODE_MAP_REV[mode_num]

        return {
            "continuous": mode_settings[0],
            "twoway": mode_settings[1],
            "trigger": mode_settings[2],
            "const_freq_step": mode_settings[3]
        }

    def sweep_speed(self, val=None):
        """
        Set the speed of the continuous sweep, in nm/s. If a new value
        is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The sweep speed of the laser, in nm/s.
            Range: 1.0 - 100 (nm/s)
            Step: 0.1 (nm/s)

        Returns
        -------
        Quantity
            The sweep speed of the laser in nm/s, with its units.

        >>> laser.sweep_speed()
        <Quantity(26.0, 'nanometer / second')>
        >>> laser.sweep_speed(25)
        <Quantity(25.0, 'nanometer / second')>
        """

        return Q_(float(self._set_var("SN", 1, val)), 'nm / s')

    def sweep_step_wavelength(self, val=None):
        """
        Set the size of each step in the stepwise sweep. If a new
        value is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The step size in the stepwise sweep in nanometers.
            Range: 0.0001 - 160 (nm)
            Step: 0.0001 (nm)

        Returns
        -------
        Quantity
            The set step size in a stepwise sweep in nm, and its units.

        >>> laser.sweep_step_wavelength()
        <Quantity(1.0, 'nanometer')>
        >>> laser.sweep_step_wavelength(2.2)
        <Quantity(2.2, 'nanometer')>
        """

        return Q_(float(self._set_var("WW", 4, val)), 'nm')

    def sweep_step_frequency(self, val=None):
        """
        Set the size of each step in the stepwise sweep when constant
        frequency intervals are enabled. If a new value is not
        provided, the current one will be returned. Units: THz

        Parameters
        ----------
        val : float, optional
            The step size of each step in the stepwise sweep in terahertz.
            Range: 0.00002 - 19.76219 (THz)
            Step: 0.00001 (THz)

        Returns
        -------
        Quantity
            The set step size in THz, and its units.

        >>> laser.sweep_step_frequency()
        <Quantity(0.1, 'terahertz')>
        >>> laser.sweep_step_frequency(0.24)
        <Quantity(0.24, 'terahertz')>
        """

        return Q_(float(self._set_var("WF", 5, val)), 'THz')

    def sweep_step_time(self, val=None):
        """
        Set the duration of each step in the stepwise sweep. If a new
        value is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The duration of each step in seconds.
            Range: 0 - 999.9 (s)
            Step: 0.1 (s)

        Returns
        -------
        Quantity
            The set duration of each step in seconds.

        >>> laser.sweep_step_time()
        <Quantity(0.5, 'second')>
        >>> laser.sweep_step_time(0.8)
        <Quantity(0.8, 'second')>
        """

        return Q_(float(self._set_var("SB", 1, val)), 's')

    def sweep_delay(self, val=None):
        """
        Set the time between consecutive sweeps in continuous mode. If
        a new value is not provided, the current one will be returned.

        Parameters
        ----------
        val : float, optional
            The delay between sweeps in seconds.
            Range: 0 - 999.9 (s)
            Step: 0.1 (s)

        Returns
        -------
        Quantity
            The set delay between sweeps in seconds.

        >>> laser.sweep_delay()
        <Quantity(0.0, 'second')>
        >>> laser.sweep_delay(1.5)
        <Quantity(1.5, 'second')>
        """

        return Q_(float(self._set_var("SA", 1, val)), 's')

    def sweep_start_wavelength(self, val=None):
        """
        Sets the start wavelength of a sweep.

        Sets the starting wavelength for subsequent sweeps. If no value
        is specified, the current starting wavelength setting is returned.

        Parameters
        ----------
        val : float, optional
            The starting value of the wavelength sweep in nanometers.
            Step: 0.0001 (nm)

        Returns
        -------
        Quantity
            The current sweep start wavelength in nm, and its units.

        >>> laser.sweep_start_wavelength()
        <Quantity(1500.0, 'nanometer')>
        >>> laser.sweep_start_wavelength(1545)
        <Quantity(1545.0, 'nanometer')>
        """

        return Q_(float(self._set_var("SS", 4, val)), 'nm')

    def sweep_start_frequency(self, val=None):
        """
        Sets the start frequency of a sweep.

        Sets the starting frequency for subsequent sweeps. If no value
        is specified, the current starting frequency setting is returned.

        Parameters
        ----------
        val : float, optional
            The starting value of the frequency sweep in terahertz.
            Step: 0.00001 (THz)

        Returns
        -------
        Quantity
            The current sweep start frequency in THz, and its units.

        >>> laser.sweep_start_frequency()
        <Quantity(199.86164, 'terahertz')>
        >>> laser.sweep_start_frequency(196)
        <Quantity(195.99999, 'terahertz')>
        """

        return Q_(float(self._set_var("FS", 5, val)), 'THz')

    def sweep_end_wavelength(self, val=None):
        """
        Sets the end wavelength of a sweep.

        Sets the ending wavelength for subsequent sweeps. If no value
        is specified, the current ending wavelength setting is returned.

        Parameters
        ----------
        val : float, optional
            The ending value of the wavelength sweep in nanometers.
            Step: 0.0001 (nm)

        Returns
        -------
        Quantity
            The current sweep end wavelength in nm, and its units.

        >>> laser.sweep_end_wavelength()
        <Quantity(1630.0, 'nanometer')>
        >>> laser.sweep_end_wavelength(1618)
        <Quantity(1618.0, 'nanometer')>
        """

        return Q_(float(self._set_var("SE", 4, val)), 'nm')

    def sweep_end_frequency(self, val=None):
        """
        Sets the end frequency of a sweep.

        Sets the ending frequency for subsequent sweeps. If no value
        is specified, the current ending frequency setting is returned.

        Parameters
        ----------
        val : float, optional
            The ending value of the frequency sweep in THz.
            Step: 0.00001 (THz)

        Returns
        -------
        Quantity
            The current sweep end frequency in THz, and its units.

        >>> laser.sweep_end_frequency()
        <Quantity(183.92175, 'terahertz')>
        >>> laser.sweep_end_frequency(185.5447)
        <Quantity(185.5447, 'terahertz')>
        """

        return Q_(float(self._set_var("FF", 5, val)), 'THz')

    def open_shutter(self):
        """
        Opens the laser's shutter.
        """
        
        return self.query("SO")

    def close_shutter(self):
        """
        Opens the laser's shutter.
        """
        
        return self.query("SC")

    def trigger_enable_output(self):
        """
        Enables the output trigger signal.
        """

        self.query("TRE")

    def trigger_disable_output(self):
        """
        Disables the output trigger signal.
        """

        self.query("TRD")

    def trigger_get_mode(self):
        current_state = self.query("TM")
        if current_state == 1:
            return "Stop"
        elif current_state == 2:
            return "Start"
        elif current_state == 3:
            return "Step"

    def trigger_set_mode(self,val=None):
        mode = 0
        if val == "None" or val == None:
            mode = 0
        elif val == "Stop":
            mode = 1
        elif val == "Start":
            mode = 2
        elif val == "Step":
            mode = 3
        else:
            raise ValueError("Invalide output trigger mode supplied. Choose from None, Stop, Start, and Step.")
        current_state = int(self.query("TM{}".format(mode)))
        if current_state == 1:
            return "Stop"
        elif current_state == 2:
            return "Start"
        elif current_state == 3:
            return "Step"

    def trigger_set_step(self,step):
        return self._set_var("TW", 4, val=step)


    def wavelength_logging_number(self):
        """
        Returns the number of wavelength points stored in the wavelength
        logging feature.

        Returns
        -------
        int
            A value between 0 and 65535, the number of recorded data points.

        >>> laser.wavelength_logging_number()
        5001
        """
        return int(self.query("TN"))

    def wavelength_logging(self):
        """
        Creates a list of all the wavelength points logged into the laser's
        buffer. Assumes that all the correct sweep and triggering protocol
        are met (see manual page 6-5).
        """
        # stop laser from outputting
        self.query("SU")

        # First, get the number of wavelength points
        num_points = self.wavelength_logging_number()

        # Preallocate arrays
        wavelength_points = []

        # Now petition the laser for the wavelength points
        command = "TA"
        # if sys.version_info.major >= 3:
        #     command = command.encode("ASCII")
        # self.device.write(command + self.terminator)
        self.device.write(command)
        time.sleep(0.1)

        # Iterate through wavelength points
        for nWave in range(int(num_points)):
            while True:
                try:
                    in_byte = self.device.read(4)
                    current_wavelength = float(struct.unpack(">I", in_byte)[0]) / 1e4
                    break
                except:
                    print('Failed to read in wavelength data.')
                    pass

            wavelength_points.append(current_wavelength)

        # stop laser from outputting
        self.query("SU")
        return wavelength_points

    def print_status(self):
        """
        Query the status of the laser and print its results.
        """
        status = self.query("SU")

        # Check if LD is on
        self.is_on = True if int(status) < 0 else False

        return status 
