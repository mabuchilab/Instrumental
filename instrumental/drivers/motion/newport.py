# -*- coding: utf-8 -*-
# Copyright 2020 Martin Cross
# 
#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2020 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
"""
Driver module for Newport motion controllers. Supports:

* ESP300
"""
import numpy
import re
from time import sleep
from enum import Enum
from . import Motion
from .. import Facet, MessageFacet, SCPI_Facet, VisaMixin, validators
from ..util import visa_timeout_context, check_enums
from ...log import get_logger
from ... import Q_

log = get_logger(__name__)

_SUBCLASS_IDN_SRCPATTERN = {
    # 'subclass': 're.search_pattern'
    'ESP300': 'ESP300'
}


def _check_visa_support(visa_rsrc):
    with visa_timeout_context(visa_rsrc, 50):
        # Assume Newport motion controllers use the same '\r' write termination
        visa_rsrc.write_termination = '\r'
        try:
            # Check if/which Newport motion controller we are connected to
            resp = visa_rsrc.query('*IDN?')
            for subclass in _SUBCLASS_IDN_SRCPATTERN.keys():
                if re.search(_SUBCLASS_IDN_SRCPATTERN[subclass], resp) is not None:
                    visa_rsrc.clear()
                    return subclass
        except:
            pass
    return None


class AxisError(Exception):
    """ Raised when a particular axis causes an error for
    the Newport ESP300. """

    MESSAGES = {
        '00': 'MOTOR TYPE NOT DEFINED',
        '01': 'PARAMETER OUT OF RANGE',
        '02': 'AMPLIFIER FAULT DETECTED',
        '03': 'FOLLOWING ERROR THRESHOLD EXCEEDED',
        '04': 'POSITIVE HARDWARE LIMIT DETECTED',
        '05': 'NEGATIVE HARDWARE LIMIT DETECTED',
        '06': 'POSITIVE SOFTWARE LIMIT DETECTED',
        '07': 'NEGATIVE SOFTWARE LIMIT DETECTED',
        '08': 'MOTOR / STAGE NOT CONNECTED',
        '09': 'FEEDBACK SIGNAL FAULT DETECTED',
        '10': 'MAXIMUM VELOCITY EXCEEDED',
        '11': 'MAXIMUM ACCELERATION EXCEEDED',
        '12': 'Reserved for future use',
        '13': 'MOTOR NOT ENABLED',
        '14': 'Reserved for future use',
        '15': 'MAXIMUM JERK EXCEEDED',
        '16': 'MAXIMUM DAC OFFSET EXCEEDED',
        '17': 'ESP CRITICAL SETTINGS ARE PROTECTED',
        '18': 'ESP STAGE DEVICE ERROR',
        '19': 'ESP STAGE DATA INVALID',
        '20': 'HOMING ABORTED',
        '21': 'MOTOR CURRENT NOT DEFINED',
        '22': 'UNIDRIVE COMMUNICATIONS ERROR',
        '23': 'UNIDRIVE NOT DETECTED',
        '24': 'SPEED OUT OF RANGE',
        '25': 'INVALID TRAJECTORY MASTER AXIS',
        '26': 'PARAMETER CHARGE NOT ALLOWED',
        '27': 'INVALID TRAJECTORY MODE FOR HOMING',
        '28': 'INVALID ENCODER STEP RATIO',
        '29': 'DIGITAL I/O INTERLOCK DETECTED',
        '30': 'COMMAND NOT ALLOWED DURING HOMING',
        '31': 'COMMAND NOT ALLOWED DUE TO GROUP',
        '32': 'INVALID TRAJECTORY MODE FOR MOVING'
    }

    def __init__(self, code):
        self.axis = str(code)[0]
        self.error = str(code)[1:]
        self.message = self.MESSAGES[self.error]

    def __str__(self):
        return "Newport ESP300 axis %s reported the error: %s" % (
            self.axis, self.message)


class GeneralError(Exception):
    """ Raised when the Newport ESP300 has a general error.
    """

    MESSAGES = {
        '1': 'PCI COMMUNICATION TIME-OUT',
        '4': 'EMERGENCY SOP ACTIVATED',
        '6': 'COMMAND DOES NOT EXIST',
        '7': 'PARAMETER OUT OF RANGE',
        '8': 'CABLE INTERLOCK ERROR',
        '9': 'AXIS NUMBER OUT OF RANGE',
        '13': 'GROUP NUMBER MISSING',
        '14': 'GROUP NUMBER OUT OF RANGE',
        '15': 'GROUP NUMBER NOT ASSIGNED',
        '17': 'GROUP AXIS OUT OF RANGE',
        '18': 'GROUP AXIS ALREADY ASSIGNED',
        '19': 'GROUP AXIS DUPLICATED',
        '16': 'GROUP NUMBER ALREADY ASSIGNED',
        '20': 'DATA ACQUISITION IS BUSY',
        '21': 'DATA ACQUISITION SETUP ERROR',
        '23': 'SERVO CYCLE TICK FAILURE',
        '25': 'DOWNLOAD IN PROGRESS',
        '26': 'STORED PROGRAM NOT STARTED',
        '27': 'COMMAND NOT ALLOWED',
        '29': 'GROUP PARAMETER MISSING',
        '30': 'GROUP PARAMETER OUT OF RANGE',
        '31': 'GROUP MAXIMUM VELOCITY EXCEEDED',
        '32': 'GROUP MAXIMUM ACCELERATION EXCEEDED',
        '22': 'DATA ACQUISITION NOT ENABLED',
        '28': 'STORED PROGRAM FLASH AREA FULL',
        '33': 'GROUP MAXIMUM DECELERATION EXCEEDED',
        '35': 'PROGRAM NOT FOUND',
        '37': 'AXIS NUMBER MISSING',
        '38': 'COMMAND PARAMETER MISSING',
        '34': 'GROUP MOVE NOT ALLOWED DURING MOTION',
        '39': 'PROGRAM LABEL NOT FOUND',
        '40': 'LAST COMMAND CANNOT BE REPEATED',
        '41': 'MAX NUMBER OF LABELS PER PROGRAM EXCEEDED'
    }

    def __init__(self, code):
        self.error = str(code)
        self.message = self.MESSAGES[self.error]

    def __str__(self):
        return "Newport ESP300 reported the error: %s" % (
            self.message)


class Axis(object):
    """ Represents an axis of the Newport ESP300 Motor Controller.

    Each axis can have independent parameters from the other axes.

    Mapping of commands:
    --------------------
    AC  x not implemented (future dev) 
    AE  x not implemented (future dev) 
    AF  x not implemented (future dev) 
    AG  x not implemented (future dev) 
    AU  x not implemented (future dev) 
    BA  x not implemented (future dev) 
    BK  x not implemented (future dev) 
    BL  x not implemented (future dev) 
    BM  x not implemented (future dev) 
    BN  x not implemented (future dev) 
    BP  x not implemented (future dev)
    BQ  x not implemented (future dev) 
    CL  x not implemented (future dev) 
    CO  x not implemented (future dev) 
    DB  x not implemented (future dev) 
    DH  -> home_pos (property)
    DP  -> target_pos (property)
    DV  x not implemented (future dev) 
    FE  x not implemented (future dev) 
    FP  -> pos_display_res (property)
    FR  x not implemented (future dev) 
    GR  x not implemented (future dev) 
    ID  -> stage_id (property)
    JH  -> jog_high_speed (property)
    JK  x not implemented (future dev) 
    JW  -> jog_low_speed (property)
    KD  x not implemented (future dev) 
    KI  x not implemented (future dev) 
    KP  x not implemented (future dev) 
    KS  x not implemented (future dev) 
    MD  -> motion_done (property)
    MF  -> motor_state (property)
    MO  -> motor_state (property)
    MT  ->
    MV  x not implemented (future dev) 
    MZ  ->
    OH  ->
    OL  ->
    OM  ->
    OR  ->
    PA  ->
    PR  ->
    QD  x not implemented (future dev) 
    QG  x not implemented (future dev) 
    QI  x not implemented (future dev) 
    QM  ->
    QR  x not implemented (future dev) 
    QS  x not implemented (future dev) 
    QT  x not implemented (future dev) 
    QV  x not implemented (future dev)  
    SH  ->
    SL  ->
    SN  ->
    SR  ->
    SS  x not implemented (future dev) 
    ST  ->
    SU  ->
    TJ  x not implemented (future dev) 
    TP  ->
    TV  ->
    VA  ->
    VB  x not implemented (future dev) 
    VF  x not implemented (future dev) 
    VU  x not implemented (future dev) 
    WP  x not implemented (future dev) 
    WS  x not implemented (future dev) 
    ZA  x not implemented (future dev) 
    ZB  x not implemented (future dev) 
    ZE  x not implemented (future dev) 
    ZF  x not implemented (future dev) 
    ZH  x not implemented (future dev) 
    ZS  x not implemented (future dev) 

    """

    def __init__(self, axis, controller):
        self.axis = axis
        self.controller = controller

    # def _AxisFacet(self, msg, convert=None, readonly=False, **kwds):
    #     """Facet factory that prepends the axis number to SCPI messages

    #     Parameters
    #     ----------
    #     msg : str
    #         Base message used to create SCPI get- and set-messages. For example, if `msg='voltage'`, the
    #         get-message is `'voltage?'` and the set-message becomes `'voltage {}'`, where `{}` gets
    #         filled in by the value being set.
    #     convert : function or callable
    #         Function that converts both the string returned by querying the instrument and the set-value
    #         before it is passed to `str.format()`. Usually something like `int` or `float`.
    #     readonly : bool, optional
    #         Whether the Facet should be read-only.
    #     **kwds :
    #         Any other keywords are passed along to the `Facet` constructor
    #     """
    #     get_msg = str(self.axis) + msg + '?'
    #     set_msg = None if readonly else str(self.axis) + msg + '{}'
    #     return MessageFacet(get_msg, set_msg, convert=convert, **kwds)

    def write(self, message, *args, **kwargs):
        """Override of controller write method.

        prepends <axis> to message string
        """
        self.controller.write(str(self.axis) + message, *args, **kwargs)

    def query(self, message, *args, **kwargs):
        """Override of controller query method.

        prepends <axis> to message string
        """
        log.debug('Using overridden query')
        return self.controller.query(str(self.axis) + message, *args, **kwargs)

    motor_state = Facet(
        name='motor_state',
        doc="""On/Off state of the motor.

        0 = motor off
        1 = motor on

        This property can be set.

        """
    )

    @motor_state.getter
    def motor_state_fget(obj):
        return int(obj.query('MO?'))

    @motor_state.setter
    def motor_state_fset(obj, value):
        if value == 1:
            obj.write('MO')
        elif value == 0:
            obj.write('MF')
        else:
            raise ValueError('Motor state must be 1 (on) or 0 (off)')

    home_pos = SCPI_Facet(
        'DH',
        readonly=False,
        name='home_pos',
        doc='''Define the home poisition of the axis.

        When set, the current position is assigned a user specified absolute
        value. Make sure to set home_preset_pos as well if you want the
        absolute position to be preserced when homing the stage. When queried,
        returns the current absolute position of the stage.

        ''',
        validator=validators.strict_range,
        values=(2e-9, 2e9),
        type=float
    )

    target_pos = SCPI_Facet(
        'DP',
        readonly=True,
        name='target_pos',
        doc='''Reads the target position.

        Typically used to read the target position while the stage is in
        motion.

        ''',
        type=float
    )

    pos_display_res = SCPI_Facet(
        'FP',
        readonly=False,
        name='pos_display_res',
        doc='''Position display resolution.

        This command is used to set the display resolution of position
        information. For instance, if nn = 4, the display will show values as
        low as 0.0001 units. If nn = 7, the display will show values in
        exponential form. If the user units (refer SN command) are in encoder
        counts or stepper increments, the position information is displayed in
        integer form, independent of the value set by this command.

        ''',
        validator=validators.strict_discrete_set,
        values=range(8),
        type=int
    )

    stage_id = SCPI_Facet(
        'ID',
        readonly=True,
        name='stage_id',
        doc='''Stage model and serial number.

        This command is used to read Newport ESP compatible positioner (stage)
        model and serial number.

        Returns:
        --------
        stage_id : str, '<model num.>, <serial, num.>'

        '''
    )

    jog_high_speed = SCPI_Facet(
        'JH',
        readonly=False,
        name='jog_high_speed',
        doc='''High jog speed of the axis.

        This command is used to set the high speed for jogging an axis. Its
        execution is immediate, meaning that the value is changed when the
        command is processed, including when motion is in progress. It can be
        used as an immediate command or inside a program.

        The allowable value is between 0 and the maximum allowed by the VU
        command.

        ''',
        validator=validators.strict_range,
        values=(0, float('inf')),  # Upper limit should be dynamic!
        type=float
    )

    jog_low_speed = SCPI_Facet(
        'JW',
        readonly=False,
        name='jog_low_speed',
        doc='''Low jog speed of the axis.

        This command is used to set the low speed for jogging an axis. Its
        execution is immediate, meaning that the value is changed when the
        command is processed, including when motion is in progress. It can be
        used as an immediate command or inside a program.

        The allowable value is between 0 and the maximum allowed by the VU
        command.

        ''',
        validator=validators.strict_range,
        values=(0, float('inf')),  # Upper limit should be dynamic!
        type=float
    )

    motion_done = SCPI_Facet(
        'MD',
        readonly=True,
        name='motion_done',
        doc='''Motion done status.

        This command is used to read the motion status for the specified axis
        n. The MD command can be used to monitor Homing, absolute, and
        relative displacement move completion status.

        ''',
        type=int
    )

    def move_to_hardware_trvl_lim(self, direction='+'):
        '''Move to the positive of negative hardware limit.

        Parameters
        ----------
        direction : str, '+' positive limit, '-' negative limit

        '''
        self.write('MT' + direction)

    # left_limit = Instrument.control(
    #     "SL?", "SL%g",
    #     """ A floating point property that controls the left software
    #     limit of the axis. """
    # )

    # right_limit = Instrument.control(
    #     "SR?", "SR%g",
    #     """ A floating point property that controls the right software
    #     limit of the axis. """
    # )

    # units = Instrument.control(
    #     "SN?", "SN%d",
    #     """ A string property that controls the displacement units of the
    #     axis, which can take values of: enconder count, motor step, millimeter,
    #     micrometer, inches, milli-inches, micro-inches, degree, gradient, radian,
    #     milliradian, and microradian.
    #     """,
    #     validator=strict_discrete_set,
    #     values={
    #         'encoder count':0, 'motor step':1, 'millimeter':2,
    #         'micrometer':3, 'inches':4, 'milli-inches':5,
    #         'micro-inches':6, 'degree':7, 'gradient':8,
    #         'radian':9, 'milliradian':10, 'microradian':11
    #     },
    #     map_values=True
    # )

    # motion_done = Instrument.measurement(
    #     "MD?",
    #     """ Returns a boolean that is True if the motion is finished.
    #     """,
    #     cast=bool
    # )



    # def enable(self):
    #     """ Enables motion for the axis. """
    #     self.write("MO")

    # def disable(self):
    #     """ Disables motion for the axis. """
    #     self.write("MF")

    # def home(self, type=1):
    #     """ Drives the axis to the home position, which may be the negative
    #     hardware limit for some actuators (e.g. LTA-HS).
    #     type can take integer values from 0 to 6.
    #     """
    #     home_type = strict_discrete_set(type, [0,1,2,3,4,5,6])
    #     self.write("OR%d" % home_type)

    # def define_position(self, position):
    #     """ Overwrites the value of the current position with the given
    #     value. """
    #     self.write("DH%g" % position)

    # def zero(self):
    #     """ Resets the axis position to be zero at the current poisiton.
    #     """
    #     self.write("DH")

    # def wait_for_stop(self, delay=0, interval=0.05):
    #     """ Blocks the program until the motion is completed. A further
    #     delay can be specified in seconds.
    #     """
    #     self.write("WS%d" % (delay*1e3))
    #     while not self.motion_done:
    #         sleep(interval)


class ESP300(Motion, VisaMixin):
    """A Newport ESP300 motion controller.

    Mapping of commands:
    --------------------
    AB  ->  
    AP  x not implemented (future dev) 
    BG  x not implemented (future dev) 
    BO  x not implemented (future dev) 
    DC  x not implemented (future dev) 
    DD  x not implemented (future dev) 
    DE  x not implemented (future dev) 
    DF  x not implemented (future dev) 
    DG  x not implemented (future dev) 
    DL  x not implemented (future dev) 
    DO  x not implemented (future dev) 
    EO  x not implemented (future dev) 
    EP  x not implemented (future dev) 
    ES  x not implemented (future dev) 
    EX  x not implemented (future dev) 
    HA  x not implemented (future dev) 
    HB  x not implemented (future dev) 
    HC  x not implemented (future dev) 
    HD  x not implemented (future dev) 
    HE  x not implemented (future dev) 
    HF  x not implemented (future dev) 
    HJ  x not implemented (future dev) 
    HL  x not implemented (future dev) 
    HN  x not implemented (future dev) 
    HO  x not implemented (future dev) 
    HP  x not implemented (future dev) 
    HQ  x not implemented (future dev) 
    HS  x not implemented (future dev) 
    HV  x not implemented (future dev) 
    HW  x not implemented (future dev) 
    HX  x not implemented (future dev) 
    HZ  x not implemented (future dev) 
    JL  x not implemented (future dev) 
    LP  x not implemented (future dev) 
    PH  ->
    QP  x not implemented (future dev) 
    RQ  ->
    RS  ->
    SA  ->
    SB  x not implemented (future dev) 
    SI  x not implemented (future dev) 
    SK  x not implemented (future dev) 
    SM  ->
    TB  -> error_msg (property)
    TE  -> error_num (property)
    TS  -> 
    TX  ->
    UF  x not implemented (future dev) 
    UH  x not implemented (future dev) 
    UL  x not implemented (future dev) 
    VE  ->
    WT  x not implemented (future dev) 
    XM  x not implemented (future dev) 
    XX  x not implemented (future dev) 
    ZU  x not implemented (future dev) 
    ZZ  x not implemented (future dev) 

    """

    _INST_PARAMS_ = ['visa_address']

    def _initialize(self):
        self.resource.write_termination = '\r'
        self.resource.read_termination = '\r\n'
        self.ax_1 = Axis(1, self)

    def close(self):
        self._rsrc.control_ren(False)  # Disable remote mode

    # Tell list_instruments how to close this VISA resource properly
    @staticmethod
    def _close_resource(resource):
        resource.control_ren(False)  # Disable remote mode

    error_msg = SCPI_Facet(
        'TB',
        readonly=True,
        doc='''Reads the error code, timestamp, and associated message.''',
    )

    error_num = SCPI_Facet(
        'TE',
        readonly=True,
        doc='''Reads the error code.''',
    )

    controller_status = SCPI_Facet(
        'TS',
        readonly=True,
        doc='''Reads the controller status byte.'''
    )

    # def __init__(self, resourceName, **kwargs):
    #     super(ESP300, self).__init__(
    #         resourceName,
    #         "Newport ESP 300 Motion Controller",
    #         **kwargs
    #     )
    #     # Defines default axes, which can be overwritten
    #     self.x = Axis(1, self)
    #     self.y = Axis(2, self)
    #     self.phi = Axis(3, self)

    # def clear_errors(self):
    #     """ Clears the error messages by checking until a 0 code is
    #     recived. """
    #     while self.error != 0:
    #         continue

    # @property
    # def errors(self):
    #     """ Returns a list of error Exceptions that can be later raised, or
    #     used to diagnose the situation.
    #     """
    #     errors = []

    #     code = self.error
    #     while code != 0:
    #         if code > 100:
    #             errors.append(AxisError(code))
    #         else:
    #             errors.append(GeneralError(code))
    #         code = self.error
    #     return errors

    # @property
    # def axes(self):
    #     """ A list of the :class:`Axis <pymeasure.instruments.newport.esp300.Axis>`
    #     objects that are present. """
    #     axes = []
    #     directory = dir(self)
    #     for name in directory:
    #         if name == 'axes':
    #             continue # Skip this property
    #         try:
    #             item = getattr(self, name)
    #             if isinstance(item, Axis):
    #                 axes.append(item)
    #         except TypeError:
    #             continue
    #         except Exception as e:
    #             raise e
    #     return axes

    # def enable(self):
    #     """ Enables all of the axes associated with this controller.
    #     """
    #     for axis in self.axes:
    #         axis.enable()

    # def disable(self):
    #     """ Disables all of the axes associated with this controller.
    #     """
    #     for axis in self.axes:
    #         axis.disable()

    # def shutdown(self):
    #     """ Shuts down the controller by disabling all of the axes.
    #     """
    #     self.disable()

