# Copyright 2016-2017 Christopher Rogers, Nate Bogdanowicz
"""
Driver for SRS model SR850 lock-in amplifier.

Note that the sr850 will not usually work with `list_instruments()`, because it uses a non-standard
termination character, and because one must first send the 'OUTX' command to specify which type of
output to use.
"""
from numpy import fromstring, float32
from enum import Enum
import visa
from ..util import check_units, check_enums
from ...errors import InstrumentTypeError
from ... import Q_

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {'SR850': ('Stanford_Research_Systems', ['SR850'])}


BYTES_PER_POINT = 4
BINARY_TIME_PER_POINT = Q_('5 ms')
ASCII_TIME_PER_POINT = Q_('16 ms')


class AlarmMode(Enum):
    off = 0
    on = 1

class ReferenceSource(Enum):
    internal = 0
    internal_sweep = 1
    external = 2

class SweepType(Enum):
    linear = 0
    logarithmic = 1

class ReferenceSlope(Enum):
    sine_zero = 0
    ttl_rising = 1
    ttl_falling = 2

class InputConfiguration(Enum):
    A = 0
    A_B = 1
    I = 2

class CurrentGain(Enum):
    oneMegaOhm = 0
    oneHundredMegaOhm = 1

class InputGround(Enum):
    floating = 0
    ground = 1

class InputCoupling(Enum):
    AC = 0
    DC = 1

class LineFilter(Enum):
    no_filters = 0
    line_notch = 1
    line_2x_notch = 2
    both_filters = 3

class Sensitivity(Enum):
    x2nV_fA = 0
    x5nV_fA = 1
    x10nV_fA = 2
    x20nV_fA = 3
    x50nV_fA = 4
    x100nV_fA = 5
    x200nV_fA = 6
    x500nV_fA = 7
    x1uV_pA = 8
    x2uV_pA = 9
    x5uV_pA = 10
    x10uV_pA = 11
    x20uV_pA = 12
    x50uV_pA = 13
    x100uV_pA = 14
    x200uV_pA = 15
    x500uV_pA = 16
    x1mV_nA = 17
    x2mV_nA = 18
    x5mV_nA = 19
    x10mV_nA = 20
    x20mV_nA = 21
    x50mV_nA = 22
    x100mV_nA = 23
    x200mV_nA = 24
    x500mV_nA = 25
    x1V_uA = 26

class ReserveMode(Enum):
    maximum = 0
    manual = 1
    minimum = 2

class TimeConstant(Enum):
    x10us = 0
    x30us = 1
    x100us = 2
    x300us = 3
    x1ms = 4
    x3ms = 5
    x10ms = 6
    x30ms = 7
    x100ms = 8
    x300ms = 9
    x1s = 10
    x3s = 11
    x10s = 12
    x30s = 13
    x100s = 14
    x300s = 15
    x1ks = 16
    x3ks = 17
    x10ks = 18
    x30ks = 19

class LowPassSlope(Enum):
    six_dB_per_octave = 0
    twelve_dB_per_octave = 1
    eighteen_dB_per_octave = 2
    twentyfour_dB_per_octave = 3

class SynchronousFilter(Enum):
    off = 0
    on = 1

class Ch1OutputSource(Enum):
    X = 0
    R = 1
    theta = 2
    trace_1 = 3
    trace_2 = 4
    trace_3 = 5
    trace_4 = 6

class Ch2OutputSource(Enum):
    Y = 0
    R = 1
    theta = 2
    trace_1 = 3
    trace_2 = 4
    trace_3 = 5
    trace_4 = 6

class OffsetSelector(Enum):
    X = 1
    Y = 2
    R = 3

class Store(Enum):
    not_stored = 0
    stored = 1

class Multiply(Enum):
    unity = 0
    X = 1
    Y = 2
    R = 3
    theta = 4
    X_n = 5
    Y_n = 6
    R_n = 7
    AuxIn1 = 8
    AuxIn2 = 9
    AuxIn3 = 10
    AuxIn4 = 11
    F = 12

class Divide(Enum):
    unity = 0
    X = 1
    Y = 2
    R = 3
    theta = 4
    X_n = 5
    Y_n = 6
    R_n = 7
    AuxIn1 = 8
    AuxIn2 = 9
    AuxIn3 = 10
    AuxIn4 = 11
    F = 12
    X_2 = 13
    Y_2 = 14
    R_2 = 15
    theta_2 = 16
    Xn_2 = 17
    Yn_2 = 18
    Rn_2 = 19
    AuxIn1_2 = 20
    AuxIn2_2 = 21
    AuxIn3_2 = 22
    AuxIn4_2 = 23
    F_2 = 24

class ScanSampleRate(Enum):
    x62_5mHz = 0
    x125mHz = 1
    x250mHz = 2
    x500mHz = 3
    x1Hz = 4
    x2Hz = 5
    x4Hz = 6
    x8Hz = 7
    x16Hz = 8
    x32Hz = 9
    x64Hz = 10
    x128Hz = 11
    x256Hz = 12
    x512Hz = 13
    trigger = 14

class ScanMode(Enum):
    single_shot = 0
    loop = 1

class TriggerStartScanMode(Enum):
    no = 0
    yes = 1

class OutputType(Enum):
    X = 1
    Y = 2
    R = 3
    theta = 4

class TraceNumber(Enum):
    one = 1
    two = 2
    three = 3
    four = 4

class AuxInput(Enum):
    one = 1
    two = 2
    three = 3
    four = 4

class Parameter(Enum):
    X = 1
    Y = 2
    R = 3
    theta = 4
    AuxIn_1 = 5
    AuxIn_2 = 6
    AuxIn_3 = 7
    AuxIn_4 = 8
    reference_frequency = 9
    trace_1 = 10
    trace_2 = 11
    trace_3 = 12
    trace_4 = 13

    def units(parameter):
        if parameter.value in [1,2,3,5,6,7,8]:
            return 'V'
        if parameter.value == 4:
            return 'degrees'
        if parameter.value == 9:
            return 'Hz'
        else:
            return None

class StatusByte(Enum):
    no_scan_in_progress = 0
    no_command_execution_in_progress = 1
    enabled_bit_in_error_status_set = 2
    enabled_bit_in_LIA_status_set = 3
    output_buffer_non_empty = 4
    enabled_bit_in_standard_status_set = 5
    service_request = 6


class SR850:
    """ Interfaces with the SRS model SR850 Lock-in Amplifier"""
    AlarmMode = AlarmMode
    ReferenceSource = ReferenceSource
    SweepType = SweepType
    ReferenceSlope = ReferenceSlope
    InputConfiguration = InputConfiguration
    CurrentGain = CurrentGain
    InputGround = InputGround
    InputCoupling = InputCoupling
    LineFilter = LineFilter
    Sensitivity = Sensitivity
    ReserveMode = ReserveMode
    TimeConstant = TimeConstant
    LowPassSlope = LowPassSlope
    SynchronousFilter = SynchronousFilter
    Ch1OutputSource = Ch1OutputSource
    Ch2OutputSource = Ch2OutputSource
    OffsetSelector = OffsetSelector
    Store = Store
    Multiply = Multiply
    Divide = Divide
    ScanSampleRate = ScanSampleRate
    ScanMode = ScanMode
    TriggerStartScanMode = TriggerStartScanMode
    OutputType = OutputType
    TraceNumber = TraceNumber
    AuxInput = AuxInput
    Parameter = Parameter
    StatusByte = StatusByte

    def _initialize(self, rs232=True):
        """ Connects to SRS850

        Parameters
        ----------
        rs232 : bool, optional
            Whether to use RS-232 or GPIB to communicate. Uses RS-232 by default
        """

        self.set_output_interface(rs232)
        self.ID = self._rsrc.query('*IDN?')
        vendor, model, SN, version = self.ID.split(',')
        if model != 'SR850':
            raise InstrumentTypeError('Instrument not SR580')

    def set_output_interface(self, rs232_interface=True):
        """ Sets the output interface.

        Default is serial (rs232_insterface=True)
        Set rs232_interface to False for GPIB
        """
        string = "OUTX {}".format((int(rs232_interface)+1)%2)
        self._rsrc.write(string)

    @check_units(frequency='Hz')
    def set_reference_frequency(self, frequency):
        """ Sets the freqeuncy of the reference source"""
        return self._set('FREQ', 'Hz', frequency)

    def get_reference_frequency(self):
        """Returns the frequency of the reference source"""
        return self._get('FREQ', 'Hz')

    @check_units(phase = 'degrees')
    def set_reference_phase(self, phase):
        """ Sets the phase shift of the reference source"""
        return self._set('PHAS', 'degrees', phase)

    def get_reference_phase(self):
        """Returns the phase shift of the reference source"""
        return self._get('PHAS', 'degrees')

    @check_enums(reference_source=ReferenceSource)
    def set_reference_source(self, reference_source):
        """ Sets the source used for the reference frequency.

        reference_source should be of type ReferenceSource
        """
        return self._set_enum('FMOD', reference_source)

    def get_reference_source(self):
        """ Returns the source used for the reference frequency.

        Returns type ReferenceSource
        """
        return self._get_enum('FMOD', ReferenceSource)

    @check_enums(sweep_type=SweepType)
    def set_frequency_sweep_type(self, sweep_type):
        """ Sets whether a sweep is linear or logarithmic.

        sweep_type should be of type SweepType
        """
        return self._set_enum('SWPT', sweep_type)

    def get_frequency_sweep_type(self):
        """ Returns whether a sweep is linear or logarithmic.

        Returns type SweepType"""
        return self._get_enum('SWPT', SweepType)

    @check_units(frequency='Hz')
    def set_start_frequency(self, frequency):
        " Sets the frequency a sweep starts at"""
        return self._set('SLLM', 'Hz', frequency)

    def get_start_frequency(self):
        """ Returns the freqeuncy that a sweep starts at"""
        return self._get('SLLM', 'Hz')

    @check_units(frequency='Hz')
    def set_stop_frequency(self, frequency):
        """Sets the frequency that a sweep stops at"""
        return self._set('SULM', 'Hz', frequency)

    @check_units(frequency='Hz')
    def get_stop_frequency(self):
        """Returns the frequency that a sweep stops at"""
        return self._get('SULM', 'Hz')

    @check_enums(reference_slope=ReferenceSlope)
    def set_reference_slope(self, reference_slope):
        """ Sets the mode with wich the reference source is discriminated.

        This is only relevant when an external source is used.

        reference_slope should be of type ReferenceSlope"""
        return self._set_enum('RSLP', reference_slope)

    def get_reference_slope(self):
        """Returns the mode with wich the reference source is discriminated."""
        return self._get_enum('RSLP', ReferenceSlope)

    def set_detection_harmonic(self, harmonic):
        """ Sets the detection harmonic """
        return self._set('HARM', None, harmonic)

    def get_detection_harmonic(self):
        """ Returns the detection harmonic """
        return self._get('HARM', None)

    @check_units(amplitude='V')
    def set_sine_amplitude(self, amplitude):
        """  Sets the amplitude of the sine output.

        Must be between 0.004 and 5V.
        (Rounds to nearest 0.002 V)
        """
        return self._set('SLVL', 'V', amplitude)

    def get_sine_amplitude(self):
        """ Returns the amplitude of the sine output, in Volts."""
        return self._get('SLVL', 'V')

    @check_enums(input_configuration=InputConfiguration)
    def set_input_configuration(self, input_configuration):
        """ Sets the input configuration.

        input_conusing should be of type InputConfiguration
        """
        return self._set_enum('ISRC', input_configuration)

    def get_input_configuration(self):
        """ Returns the input configuration."""
        return self._get_enum('ISRC', InputConfiguration)

    @check_enums(current_gain=CurrentGain)
    def set_current_gain(self, current_gain):
        """ Sets the conversion gain of the input current.

        Use the enumerator CurrentGain """
        return self._set_enum('IGAN', current_gain)

    def get_current_gain(self):
        """Returns the conversion gain of the input current """
        return self._get_enum('IGAN', CurrentGain)

    @check_enums(input_ground=InputGround)
    def set_input_ground(self, input_ground):
        """ Sets the input shield grounding mode.

        Use the enumerator InputGround"""
        return self._set_enum('IGND', input_ground)

    def get_input_ground(self):
        """ Returns the input shield grounding mode."""
        return self._get_enum('IGND', InputGround)

    @check_enums(input_coupling=InputCoupling)
    def set_input_coupling(self, input_coupling):
        """ Sets the input coupling mode
        Use the enumerator InputCoupling"""
        return self._set_enum('ICPL', input_coupling)

    def get_input_coupling(self):
        """ Returns the input couplig mode"""
        return self._get_enum('ICPL', InputCoupling)

    @check_enums(line_filter=LineFilter)
    def set_line_filter_status(self, line_filter):
        """ Sets the configuration of the line filters.

        Use the enumerator LineFilter"""
        return self._set_enum('ILIN', line_filter)

    def get_line_filter_status(self):
        """ Returns the configuratin of the line filters"""
        return self._get_enum('ILIN', LineFilter)

    @check_enums(sensitivity=Sensitivity)
    def set_sensitivity(self, sensitivity):
        """ Sets the sensitivity of the instrument.

        Use the enumerator Sensitivity"""
        return self._set_enum('SENS', sensitivity)

    def get_sensitivity(self):
        """Returns the sensitivity setting of the instrument """
        return self._get_enum('SENS', Sensitivity)

    @check_enums(reserve_mode=ReserveMode)
    def set_reserve_mode(self, reserve_mode):
        """ Sets the reserve mode of the instrument

        Use the enumerator ReserveMode"""
        return self._set_enum('RMOD', reserve_mode)

    def get_reserve_mode(self):
        """ Returns the reserve mode of the instrument."""
        return self._get_enum('RMOD', ReserveMode)

    def set_reserve(self, reserve):
        """ Sets the manual dynamic reserve.

        Reserve should be an integer
        between 0 and 5, inclusive. 0 sets the minimum reserve for the current
        time constant and sensitivity.  Each increment increases the reserve
        by 10dB. """
        return self._set('RSRV', None, reserve)

    def get_reserve(self):
        """ Returns the current value of the dynamic reserve."""
        return self._get('RSVR', None)

    @check_enums(time_constant=TimeConstant)
    def set_time_constant(self, time_constant):
        """ Sets the time constant of the instrument

        Use the enumerator TimeConstant"""
        return self._set_enum('OFLT', time_constant)

    def get_time_constant(self):
        """Get the current time constant of the instrument."""
        return self._get_enum('OFLT', TimeConstant)

    @check_enums(low_pass_slope=LowPassSlope)
    def set_low_pass_slope(self, low_pass_slope):
        """ Sets the slope for the low pass filter

        Use the enumerator LowPassSlope"""
        return self._set_enum('OFSL', low_pass_slope)

    def get_low_pass_slope(self):
        """ Returns the slope of the low pass filter."""
        return self._get_enum('OFSL', LowPassSlope)

    @check_enums(synchronous_filter=SynchronousFilter)
    def set_synchronous_filter(self, synchronous_filter):
        """ Sets the state of the synchronous filter.

        Use the enumerator SynchronousFilter.
        Note that the synchronous filter only operates if
        the detection frequency is below 200Hz"""
        return self._set_enum('SYNC', synchronous_filter)

    def get_synchronous_filter(self):
        """Returns the state of the synchronous filter."""
        return self._get_enum('SYNC', SynchronousFilter)

    @check_enums(ch1_output_source=Ch1OutputSource)
    def set_ch1_output_source(self, ch1_output_source):
        """ Sets the output source for channel 1.

        Use the enumerator Ch1OutputSource. """
        return self._set_enum('FOUT1,', ch1_output_source)

    def get_ch1_output_source(self):
        """Returns the output source for channel 1."""
        return self._get_enum('FOUT?1', Ch1OutputSource, QM=False)

    @check_enums(ch2_output_source=Ch2OutputSource)
    def set_ch2_output_source(self, ch2_output_source):
        """ Sets the output source for channel 2

        Use the enumerator Ch2OutputSource. """
        return self._set_enum('FOUT2,', ch2_output_source)

    def get_ch2_output_source(self):
        """Returns the output source for channel 2."""
        return self._get_enum('FOUT?2', Ch2OutputSource, QM=False)

    @check_enums(offset_selector=OffsetSelector)
    def set_output_offsets_and_expands(self, offset_selector, offset,
                                       expand):
        """ Sets the offsets and expands for the selected quadrature.

        offset_selector is of type OffsetSelector, and indicates which
        quadrature to use.
        Note that offset_selector should be in percent, and expand should
        be an integer between 1 and 256 """
        offset = offset
        command_string = "OEXP {}, {}, {}"
        command_string = command_string.format(offset_selector.value,
                                               offset, int(expand))
        val = self._rsrc.write(command_string)
        assert val == len(command_string)

    @check_enums(offset_selector=OffsetSelector)
    def get_output_offsets_and_expands(self, offset_selector):
        """ Returns the offsets and expands for the selected quadrature.

        offset_selector should be of type OffsetSelector"""
        command_string = "OEXP? {}".format(offset_selector.value)
        value = self._rsrc.query(command_string)
        offset, expand = value.split(',')
        return offset, expand

    @check_enums(offset_selector=OffsetSelector)
    def auto_offset(self, offset_selector):
        """ Automatically offsets the selected quadrature to zero

        offset_selector should be of type OffsetSelector """
        self._set_enum('AOFF', offset_selector)

    @check_enums(trace=TraceNumber, m1=Multiply, m2=Multiply, d=Divide,
                 store=Store)
    def set_trace_definitions(self, trace, m1,
                              m2=Multiply.unity, d=Divide.unity,
                              store=Store.stored):
        """ Sets the definition of the given trace 'trace' to be
        m1*m2/d.

        Trace should be an enumerator of Trace,
        m1 and m2 should be enumerators of Multiply,
        d should be an enumerator of Divide,
        and store should be an enumerator of Store.
        """
        m1 = m1.value
        m2 = m2.value
        d = d.value
        trace = trace.value
        store = store.value
        command_string = "TRCD {}, {}, {}, {}, {}"

        command_string = command_string.format(trace, m1, m2,
                                               d, store)
        self._rsrc.write(command_string)

    @check_enums(trace=TraceNumber)
    def get_trace_definitions(self, trace):
        """ Returns the definition of the given trace.

        Trace should be an enumerator of Trace.
        The trace definition is of the form m1*m2/d

        Returns
        --------

        m1, m2 of type Multiply
        d of type Divide
        store of type Store
        """
        command_string = "TRCD? {}".format(trace.value)
        value = self._rsrc.query(command_string)
        m1, m2, d, store = value.split(',')
        m1 = Multiply(int(m1))
        m2 = Multiply(int(m2))
        d = Divide(int(d))
        store = Store(int(store))
        return m1, m2, d, store

    @check_enums(scan_sample_rate=ScanSampleRate)
    def set_scan_sample_rate(self, scan_sample_rate):
        """ Sets the sampling rate of a scan.

        Use the enumerator ScanSampleRate. """
        return self._set_enum('SRAT', scan_sample_rate)

    def get_scan_sample_rate(self):
        """ Sets the sampling rate of a scan. """
        return self._get_enum('SRAT', ScanSampleRate)

    @check_units(scan_length='s')
    def set_scan_length(self, scan_length):
        """ Sets the scan length."""
        return self._set('SLEN', 's', scan_length)

    def get_scan_length(self):
        """Returns the scan length."""
        return self._get('SLEN', 's')

    @check_enums(scan_mode=ScanMode)
    def set_scan_mode(self, scan_mode):
        """ Sets the scan mode.
        Use the enumerator ScanMode. """
        return self._set_enum('SEND', scan_mode)

    def get_scan_mode(self):
        """Returns the scan mode."""
        return self._get_enum('SEND', ScanMode)

    def trigger(self):
        """ Initiates a trigger event. """
        self._send_command('TRIG')

    @check_enums(aux_in=AuxInput)
    def get_aux_in(self, aux_in):
        """ Returns the voltage of the specified auxillary input.

        aux_in should be of type AuxIn  """
        command_string = 'OAUX?{}'.format(aux_in.value)
        return self._get(command_string, 'V', QM=False)

    @check_enums(trigger_start_scan_mode=TriggerStartScanMode)
    def set_trigger_start_scan_mode(self, trigger_start_scan_mode):
        """ Sets the mode in which the trigger initiates a scan.

        Use the enumerator TriggerStartScanMode. """
        return self._set_enum('TSTR', trigger_start_scan_mode)

    def get_trigger_start_scan_mode(self):
        """Returns the mode in which the trigger initiates a scan."""
        return self._get_enum('TSTR', TriggerStartScanMode)

    def start_scan(self):
        """ Starts or resumes a scan/sweep.

        Has no effect if a scan is already
        in progress. """
        self._send_command('STRT')

    def pause_scan(self):
        """ Pauses a scan or sweep.

        Has no effect is no scans are in progress."""
        self._send_command('PAUS')

    def reset_scan(self):
        """ Resets a scan.

        This works whether a scan is in progress, finished, or paused.
        Note that the data buffer is erased. """
        self._send_command('REST')

    def auto_gain(self):
        """ Performs the auto-gain function.

        Note that this function does not
        return until the process has completed."""
        self._send_command('AGAN')

    def auto_reserve(self):
        """ Performs the auto-reserve function """
        self._send_command('ARSV')

    def auto_phase(self):
        """ Performs the auto-phase function """
        self._send_command('APHS')

    @check_enums(output_type=OutputType)
    def read_output(self, output_type):
        """ Returns the value of the indicated output

        use type OutputType. """
        command_string = "OUTP?{}".format(output_type.value)
        if output_type in [OutputType.X, OutputType.Y, OutputType.R]:
            units = 'V'
        else:
            units = 'degrees'
        return self._get(command_string, units, QM=False)

    @check_enums(trace_number=TraceNumber)
    def read_trace_value(self, trace_number, units=None):
        """ Returns the current value of indicated trace

        trace_number should be of enumeraror class TraceNumber.
        If specified, units are added to the returned value.
        units should be a string."""
        command_string = "OUTR? {}".format(trace_number.value)
        return self._get(command_string, units, QM=False)

    @check_enums(aux_input=AuxInput)
    def read_aux_input(self, aux_input):
        """ Returns the value of the specified aux input

        use type AuxInput"""
        command_string = "OAUX? {}".format(aux_input.value)
        return self._get(command_string, 'V', QM=False)

    def read_simultaneously(self, parameters):
        """ Returns simultaneosly the values the given parameters

        the list parameters should have between two and 6 elements of the type
        Parameter"""
        command_string = "SNAP?"
        i = 0
        for parameter in parameters:
            if i == 0:
                command_string = command_string + '{}'.format(parameter.value)
            else:
                command_string = command_string + ',{}'.format(parameter.value)
            i = i + 1
        value = self._rsrc.query(command_string)
        outputs = value.split(',')
        for i in range(len(outputs)):
            parameter = parameters[i]
            outputs[i] = Q_(outputs[i], parameter.units())
        return outputs

    @check_enums(trace_number=TraceNumber)
    def trace_length(self, trace_number):
        """ Returns the number of points in the specified trace

        use the enumerator TraceNumber """
        command_string = "SPTS? {}".format(trace_number.value)
        return self._get(command_string, None, QM=False).magnitude

    @check_enums(trace_number=TraceNumber)
    def get_trace(self, trace_number, points=None, units=None, binary=True):
        """ Returns a vector of the values stored in the indicated trace

        If get_trace times out while transferring data, the constants
        BINARY_TIME_PER_POINT and or ASCII_TIME_PER_POINT may need to be
        increased

        Parameters
        ----------

        trace_number should be an element of TraceNumber.

        points is a list of two integers - the first indicates the position
        of the first value to be read, while the second indicates the number
        of values to be read.  By default, all points are read.

        units - string indicating the proper units of the trace
        binary - boolean indicating the method of data transfer.  Using binary
        is usually about 4 times faster.
        """
        if points is None:
            points = [0, self.trace_length(trace_number)]
        if binary:
            command = 'TRCB'
        else:
            command = 'TRCA'
        command_string = "{}? {}, {}, {}".format(command, trace_number.value,
                                                 points[0], points[1])
        if binary:
            self._send_command(command_string)
            timeout = self._rsrc.timeout
            read_termination = self._rsrc.read_termination
            end_input = self._rsrc.end_input

            #Factor of 2 is so that the transfer completes before timing out
            self._rsrc.timeout = 2*BINARY_TIME_PER_POINT.to('ms').magnitude*points[1] + timeout
            self._rsrc.read_termination = None
            self._rsrc.end_input = visa.constants.SerialTermination.none
            with self._rsrc.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT):
                raw_binary, _ = self._rsrc.visalib.read(self._rsrc.session,
                                                        points[1]*BYTES_PER_POINT)
            trace = fromstring(raw_binary, dtype=float32)
            trace = trace.astype(float)
            self._rsrc.read_termination = read_termination
            self._rsrc.end_input = end_input
            self._rsrc.timeout = timeout
        else:
            timeout = self._rsrc.timeout

            #Factor of 2 is so that the transfer completes before timing out
            self._rsrc.timeout = 2*ASCII_TIME_PER_POINT.to('ms').magnitude*points[1] + timeout
            value = self._rsrc.query(command_string)
            trace = fromstring(value, sep=',')
            self._rsrc.timeout = timeout
        assert len(trace) == points[1]
        return Q_(trace, units)

    @check_enums(alarm_mode=AlarmMode)
    def set_alarm_mode(self, alarm_mode):
        """ Sets the audible alarm on or off.

        Use the enumerator AlarmMode. """
        return self._set_enum('ALRM', alarm_mode)

    def get_alarm_mode(self):
        """Returns whether the audible alarm is on or off."""
        return self._get_enum('ALRM', AlarmMode)

    def scan_in_progress(self):
        """Indicates if a scan is in progress.

        Note that a paused scan is counted as being in progress """
        status_byte = StatusByte.no_scan_in_progress
        return not self._read_status_byte(status_byte)

    def command_execution_in_progress(self):
        """ Indicates if a command is currently being executed. """
        status_byte = StatusByte.no_command_execution_in_progress
        return not self._read_status_byte(status_byte)

    def _reset(self):
        """ Resets the machine to its defaults. """
        self._send_command("*rst")

    def clear_registers(self):
        """ Clears all status registers, except for status enable registers.
        """
        self._send_command("*CLS")

    def _get(self, command_string, unit_string, QM=True):
        if QM:
            command_string = command_string + '?'
        value = self._rsrc.query(command_string)
        return Q_(value, unit_string)

    def _set(self, command_string, unit_string, value):
        value = Q_(value)
        command_string = "{} {}".format(command_string,
                                        value.to(unit_string).magnitude)
        self._send_command(command_string)

    def _get_enum(self, command_string, enum_class, QM=True):
        value = self._get(command_string, None, QM=QM)
        return enum_class(value.magnitude)

    def _set_enum(self, command_string, enum_value):
        enum_value = enum_value.value
        command_string = "{} {}".format(command_string, enum_value)
        self._send_command(command_string)

    @check_enums(status_byte=StatusByte)
    def _read_status_byte(self, status_byte):
        """ Returns a bool indicating the status byte indicated by status_byte,
        which should be a memeber of enumerator class StatusByte """
        command_string = "*STB? {}".format(status_byte.value)
        value = self._rsrc.query(command_string)
        return bool(int(value))

    def _send_command(self, command_string):
        self._rsrc.write(command_string)

    def close(self):
        self._rsrc.close()
