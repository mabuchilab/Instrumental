"""
Driver for SRS model SR44 lock-in amplifier.

Note that the sr844 will not usually work with `list_instruments()`, because it uses a non-standard
termination character, and because one must first send the 'OUTX' command to specify which type of
output to use.
"""
from numpy import fromstring, float32
from enum import Enum
import visa
from ..util import check_units, check_enums
from ...errors import InstrumentTypeError
from ... import Q_
from . import Lockin
from .. import Facet

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {'SR844': ('Stanford_Research_Systems', ['SR844'])}


BYTES_PER_POINT = 4
BINARY_TIME_PER_POINT = Q_('5 ms')
ASCII_TIME_PER_POINT = Q_('16 ms')


class AlarmMode(Enum):
    off = 0
    on = 1

class ReferenceSource(Enum):
    internal = 0
    external = 1

class Sensitivity(Enum):
    x100nV = 0
    x300nV = 1
    x1uV = 2
    x3uV = 3
    x10uV = 4
    x30uV = 5
    x100uV = 6
    x300uV = 7
    x1mV = 8
    x3mV = 9
    x10mV = 10
    x30mV = 11
    x100mV = 12
    x300mV = 13
    x1V = 14

class ReserveMode(Enum):
    off = 0
    on = 1

class WideReserveMode(Enum):
    high_reserve = 0
    normal = 0
    low_noise = 0

class CloseReserveMode(Enum):
    high_reserve = 0
    normal = 0
    low_noise = 0

class TimeConstant(Enum):
    x100us = 0
    x300us = 1
    x1ms = 2
    x3ms = 3
    x10ms = 4
    x30ms = 5
    x100ms = 6
    x300ms = 7
    x1s = 8
    x3s = 9
    x10s = 10
    x30s = 11
    x100s = 12
    x300s = 13
    x1ks = 14
    x3ks = 15
    x10ks = 16
    x30ks = 17

class LowPassSlope(Enum):
    six_dB_per_octave = 0
    twelve_dB_per_octave = 1
    eighteen_dB_per_octave = 2
    twentyfour_dB_per_octave = 3

class Ch1OutputSource(Enum):
    X = 0
    R = 1
    RdBm = 2
    Xn = 3
    AuxIn = 4

class Ch2OutputSource(Enum):
    Y = 0
    theta = 1
    Yn = 2
    YndBm = 3
    AuxIn = 4

class ExpandSelector(Enum):
    x1 = 0
    x10 = 1
    x100 = 2

class OutputType(Enum):
    X = 1
    Y = 2
    R = 3
    RdBm = 4
    theta = 5

class AuxInput(Enum):
    one = 1
    two = 2
    three = 3
    four = 4

class ScanMode(Enum):
    single_shot = 0
    loop = 1

class TriggerStartScanMode(Enum):
    no = 0
    yes = 1

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


class SR844(Lockin):
    """ Interfaces with the SRS model SR844 Lock-in Amplifier"""
    AlarmMode = AlarmMode
    ReferenceSource = ReferenceSource
    Sensitivity = Sensitivity
    ReserveMode = ReserveMode
    WideReserveMode = WideReserveMode
    CloseReserveMode = CloseReserveMode
    TimeConstant = TimeConstant
    LowPassSlope = LowPassSlope
    Ch1OutputSource = Ch1OutputSource
    Ch2OutputSource = Ch2OutputSource
    OutputType = OutputType
    AuxInput = AuxInput
    Parameter = Parameter
    StatusByte = StatusByte

    def _initialize(self, rs232=False):
        """ Connects to SRS850

        Parameters
        ----------
        rs232 : bool, optional
            Whether to use RS-232 or GPIB to communicate. Uses GPIB by default
        """
        self._rsrc.clear()
        self.set_output_interface(rs232)
        self._rsrc.read_termination = '\n'
        self.ID = self._rsrc.query('*IDN?')
        vendor, model, SN, version = self.ID.split(',')
        if model != 'SR844':
            raise InstrumentTypeError('Instrument not SR844')

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

    @property
    def frequency(self):
        return self.get_reference_frequency()

    @frequency.setter
    def frequency(self, frequency):
        self.set_reference_frequency(frequency)

    @check_units(phase='degrees')
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

    def set_detection_harmonic(self, harmonic):
        """ Sets the detection harmonic """
        harmonic = int(harmonic)
        if harmonic not in [1, 2]:
            raise ValueError('Harmonic must be either 1 or 2.')
        return self._set('HARM', None, harmonic)

    def get_detection_harmonic(self):
        """ Returns the detection harmonic """
        return self._get('HARM', None)

    @check_enums(sensitivity=Sensitivity)
    def set_sensitivity(self, sensitivity):
        """ Sets the sensitivity of the instrument.

        Use the enumerator Sensitivity"""
        return self._set_enum('SENS', sensitivity)

    def get_sensitivity(self):
        """Returns the sensitivity setting of the instrument """
        return self._get_enum('SENS', Sensitivity)

    @property
    def sensitivity(self):
        return Q_(self.get_sensitivity().name[1:])

    @sensitivity.setter
    @check_units(sensitivity='V')
    def sensitivity(self, sensitivity):
        string = '{:~.0f}'.format(sensitivity.to_compact())
        string = 'x' + string.replace(' ', '')
        self.set_sensitivity(Sensitivity[string])

    @check_enums(reserve_mode=ReserveMode)
    def set_reserve_mode(self, reserve_mode):
        """ Sets the reserve mode of the instrument

        Use the enumerator ReserveMode"""
        return self._set_enum('RMOD', reserve_mode)

    def get_reserve_mode(self):
        """ Returns the reserve mode of the instrument."""
        return self._get_enum('RMOD', ReserveMode)

    @check_enums(reserve=WideReserveMode)
    def set_wide_reserve(self, reserve_mode):
        """ Sets the wide dynamic reserve."""
        return self._set('WRSV', None, reserve_mode)

    def get_wide_reserve(self):
        """ Returns the current value of the wide dynamic reserve."""
        return self._get_enum('WRSV', WideReserveMode)

    @check_enums(reserve=CloseReserveMode)
    def set_close_reserve(self, reserve_mode):
        """ Sets the close dynamic reserve. """
        return self._set('CRSV', None, reserve_mode)

    def get_close_reserve(self):
        """ Returns the current value of the wide dynamic reserve."""
        return self._get_enum('CRSV', CloseReserveMode)

    @check_enums(time_constant=TimeConstant)
    def set_time_constant(self, time_constant):
        """ Sets the time constant of the instrument

        Use the enumerator TimeConstant"""
        return self._set_enum('OFLT', time_constant)

    def get_time_constant(self):
        """Get the current time constant of the instrument."""
        return self._get_enum('OFLT', TimeConstant)

    @property
    def time_constant(self):
        return Q_(self.get_time_constant().name[1:])

    @time_constant.setter
    @check_units(time_constant='s')
    def time_constant(self, time_constant):
        string = '{:~.0f}'.format(time_constant.to_compact())
        string = 'x' + string.replace(' ', '')
        self.set_time_constant(TimeConstant[string])

    @check_enums(low_pass_slope=LowPassSlope)
    def set_low_pass_slope(self, low_pass_slope):
        """ Sets the slope for the low pass filter

        Use the enumerator LowPassSlope"""
        return self._set_enum('OFSL', low_pass_slope)

    def get_low_pass_slope(self):
        """ Returns the slope of the low pass filter."""
        return self._get_enum('OFSL', LowPassSlope)

    @check_enums(ch1_output_source=Ch1OutputSource)
    def set_ch1_output_source(self, ch1_output_source):
        """ Sets the output source for channel 1.

        Use the enumerator Ch1OutputSource. """
        return self._set_enum('DDEF1,', ch1_output_source)

    def get_ch1_output_source(self):
        """Returns the output source for channel 1."""
        return self._get_enum('DDEF?1', Ch1OutputSource, QM=False)

    @check_enums(ch2_output_source=Ch2OutputSource)
    def set_ch2_output_source(self, ch2_output_source):
        """ Sets the output source for channel 2

        Use the enumerator Ch2OutputSource. """
        return self._set_enum('DDEF2,', ch2_output_source)

    def get_ch2_output_source(self):
        """Returns the output source for channel 2."""
        return self._get_enum('DDEF?2', Ch2OutputSource, QM=False)

    # TODO:
    # GET OFFSET and EXPAND
    #
    #    @check_enums(offset_selector=OffsetSelector)
    #def set_output_offsets_and_expands(self, offset_selector, offset,
    #                                   expand):
    #    """ Sets the offsets and expands for the selected quadrature.

    #    offset_selector is of type OffsetSelector, and indicates which
    #    quadrature to use.
    #    Note that offset_selector should be in percent, and expand should
    #    be an integer between 1 and 256 """
    #    offset = offset
    #    command_string = "OEXP {}, {}, {}"
    #    command_string = command_string.format(offset_selector.value,
    #                                           offset, int(expand))
    #    val = self._rsrc.write(command_string)
    #    assert val == len(command_string)
    #@check_enums(offset_selector=OffsetSelector)
    #def get_output_offset(self, channel, offset_selector):
    #    """ Returns the offsets and expands for the selected quadrature.
    #
    #    offset_selector should be of type OffsetSelector.
    #    The return value is in percent."""
    #    command_string = "OEXP? {}".format(offset_selector.value)
    #    value = self._rsrc.query(command_string)
    #    offset, expand = value.split(',')
    #    return offset, expand
    #
    #@check_enums(expand_selector=ExpandSelector)
    #def get_output_expand(self, channel, expand_selector):
    #    """ Returns the expand for the selected quadrature.
    #
    #    expand_selector should be a type of ExpandSelector"""

    #
    #@check_enums(offset_selector=OffsetSelector)
    #def auto_offset(self, offset_selector):
    #    """ Automatically offsets the selected quadrature to zero
    #
    #    offset_selector should be of type OffsetSelector """
    #    self._set_enum('AOFF', offset_selector)

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

    def read_trace_value(self, channel, units=None):
        """ Returns the current value of indicated tchannel

        If specified, units are added to the returned value.
        units should be a string."""
        if int(channel) not in [1, 2]:
            raise ValueError('Select channel 1 or 2')
        command_string = "OUTR? {}".format(channel)
        return self._get(command_string, units, QM=False)

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

    def trace_length(self, channel):
        """ Returns the number of points in the specified channel."""

        channel = int(channel)
        if channel not in [1, 2]:
            raise ValueError('Channel must be either 1 or 2')
        command_string = "SPTS? {}".format(channel)
        return self._get(command_string, None, QM=False).magnitude


    def get_trace(self, channel, points=None, units=None, binary=True):
        """ Returns a vector of the values stored in the indicated trace

        If get_trace times out while transferring data, the constants
        BINARY_TIME_PER_POINT and or ASCII_TIME_PER_POINT may need to be
        increased

        Parameters
        ----------

        Channel is an integer, either 1 or 2

        points is a list of two integers - the first indicates the position
        of the first value to be read, while the second indicates the number
        of values to be read.  By default, all points are read.

        units - string indicating the proper units of the trace
        binary - boolean indicating the method of data transfer.  Using binary
        is usually about 4 times faster.
        """
        channel = int(channel)
        if channel not in [1, 2]:
            raise ValueError('Channel must be either 1 or 2')

        if points is None:
            points = [0, self.trace_length(channel)]
        if binary:
            command = 'TRCB'
        else:
            command = 'TRCA'
        command_string = "{}? {}, {}, {}".format(command, channel,
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

    def get_lia_status(self, clear_registers=False):
        """Returns the LIA status byte"""
        value = self._rsrc.query('LIAS?')
        if clear_registers:
            self._rsrc.write('*CLS')
        return value

    def _send_command(self, command_string):
        self._rsrc.write(command_string)

    def close(self):
        self._rsrc.close()
