# -*- coding: utf-8 -*-
# Copyright 2016-2017 Nate Bogdanowicz
"""
Driver module for HP/Agilent digital multimeters. So far we've added support
for the 34401A and 3478A models.
"""
from enum import Enum
from . import Multimeter
from ..util import as_enum, check_enums
from ... import u, Q_
import numpy as np

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'HP34000': ('HEWLETT-PACKARD', ['34401A']),
    'HP3478A': ('HEWLETT-PACKARD', ['3478A'])
}



class TriggerSource(Enum):
    bus = 0
    immediate = imm = 1
    ext = 2
    external = 2


class MultimeterError(Exception):
    pass


#### HP3478A driver code


class HP3478A(Multimeter):
    """Class definition for an HP 3478A digital multimeter.
    """
    def _initialize(self):
        self._meas_units = None
        self._rsrc.write_termination = '\r\n'
        self._rsrc.read_termination = '\r\n'
        self._rsrc.timeout=10000 # set a long timeout in case of autorange delay
        ### define command string dictionaries ###
        ## measurement functions
        self.functions = {'DC voltage':'F1',
                         'AC voltage':'F2',
                         'two wire resistance':'F3',
                         'four wire resistance':'F4',
                         'DC current':'F5',
                         'AC current':'F6',
                         'extended ohms':'F7'}
        ## ranges
        # 'R-2' # 30mV range, DC Voltage only
        # 'R-1' # AC or DC 300mV or 300mA
        # 'R0' # AC or DC 3V or 3A
        # 'R1' # AC or DC 30V or 30Ohm
        # 'R2' # AC or DC 300V or 300Ohm
        # 'R3' # 3kOhm
        # 'R4' # 30kOhm
        # 'R5' # 300kOhm
        # 'R6' # 3MOhm
        # 'R7' # 30MOhm
        # 'RA' # Auto-range
        self.ranges = {'30m':'R-2',
                        '300m':'R-1',
                        '3':'R0',
                        '30':'R1',
                        '300':'R2',
                        '3k':'R3',
                        '30k':'R4',
                        '300k':'R5',
                        '3M':'R6',
                        '30M':'R7',
                        'auto':'RA'}
        ## display digits, measurement precision
        # 'N3' # display 3.5 digits,integrate over 0.1 power line cycles
        # 'N4' # display 4.5 digits,integrate over 1 power line cycles
        # 'N5' # display 5.5 digits,integrate over 10 power line cycles
        self.precisions = {'low':'N3','medium':'N4','high':'N5'}
        ## trigger settings
        self.triggers = {'internal':'T1',
                        'external':'T2',
                        'single':'T3',
                        'hold':'T4',
                        'fast':'T5'}
        # auto zero
        self.autozero = {'off':'Z0','on':'Z1'}
        # display commands
        self.display = {'normal_display':'D1',
                        'display_text':'D2', #follow this with up to 12 ASCII chars to print
                        'display_text_turn_off_annunciators':'D3'} # seems weird don't use

    def _autozero(self,autozero_bool):
        if autozero_bool:
            return self.autozero['on']
        else:
            return self.autozero['off']

    def _configure(self,function_str,range='auto',precision='low',autozero=True,trigger='internal',verbose=False):
        command = function_str + self.ranges[range] + self._autozero(autozero) + self.precisions[precision] + self.triggers[trigger]
        if verbose:
            print('command string: ' + command)
        self._rsrc.write(command)

    def read(self,n_tries=10):
        n = 0
        while n < n_tries:
            out_str = self._rsrc.read()
            if out_str:
                return np.float(out_str) * self._meas_units
            else:
                n += 1
        raise Exception('no result available from HP3478A DMM, has it triggered?')

    def config_dc_voltage(self,**kwargs):
        self._configure(self.functions['DC voltage'],**kwargs)
        self._meas_units = u.volt

    def config_dc_current(self,**kwargs):
        self._configure(self.functions['DC current'],**kwargs)
        self._meas_units = u.ampere

    def config_ac_voltage(self,**kwargs):
        self._configure(self.functions['AC voltage'],**kwargs)
        self._meas_units = u.volt

    def config_ac_current(self,**kwargs):
        self._configure(self.functions['AC current'],**kwargs)
        self._meas_units = u.ampere

    def config_two_wire_resistance(self,**kwargs):
        self._configure(self.functions['two wire resistance'],**kwargs)
        self._meas_units = u.ohm

    def config_four_wire_resistance(self,**kwargs):
        self._configure(self.functions['four wire resistance'],**kwargs)
        self._meas_units = u.ohm

    def config_extended_ohms(self,**kwargs):
        self._configure(self.functions['extended ohms'],**kwargs)
        self._meas_units = u.ohm



class HP34000(Multimeter):
    """Class definition for an HP 34000 series digital multimeter.
    This was developed for an HP 34401A, but the commands should be similar for
    other instruments in this series.
    """

    def _initialize(self):
        self._meas_units = None
        self._rsrc.write_termination = '\r\n'
        self._rsrc.read_termination='\n'
        self._rsrc.timeout=3000
        ## old _initialize (possibly for RS232 interface?, doesn't seem to work with GPIB)
        # self._rsrc.write('system:remote')
        # self._rsrc.write('trig:count 512')

    def _handle_err_info(self, err_info):
        code, msg = err_info.strip().split(',')
        code = int(code)
        if code != 0:
            raise MultimeterError(msg[1:-1])

    def _query(self, message):
        #resp, err_info = self._rsrc.query(message + ';:syst:err?').split(';')
        #self._handle_err_info(err_info)
        resp = self._rsrc.query(message)
        return resp

    def _write(self, message):
        # err_info = self._rsrc.query(message + ';:syst:err?')
        # self._handle_err_info(err_info)
        self._rsrc.write(message)

    def _make_rr_str(self, val):
        if val in ('min', 'max', 'def'):
            return val
        else:
            q = Q_(val)
            return str(q.m_as(self._meas_units))

    def _make_range_res_str(self, range, res):
        if range is None and res is not None:
                raise ValueError('You may only specify `res` if `range` is given')

        strs = [self._make_rr_str(r) for r in (range, res) if r is not None]
        return ','.join(strs)

    def config_dc_voltage(self, range=None, resolution=None):
        """ Configure the multimeter to perform a DC voltage measurement.

        Parameters
        ----------
        range : Quantity, 'min', 'max', or 'def'
            Expected value of the input signal
        resolution : Quantity, 'min', 'max', or 'def'
            Resolution of the measurement, in measurement units
        """
        self._meas_units = u.volts
        self._write('func "volt:dc"')

        if range is not None:
            self._write('volt:range {}'.format(self._make_rr_str(range)))

        if resolution is not None:
            self._write('volt:res {}'.format(self._make_rr_str(resolution)))

    def config_dc_current(self, range=None, resolution=None):
        """ Configure the multimeter to perform a DC current measurement.

        Parameters
        ----------
        range : Quantity, 'min', 'max', or 'def'
            Expected value of the input signal
        resolution : Quantity, 'min', 'max', or 'def'
            Resolution of the measurement, in measurement units
        """
        self._meas_units = u.ampere
        self._write('func "curr:dc"')

        if range is not None:
            self._write('curr:range {}'.format(self._make_rr_str(range)))

        if resolution is not None:
            self._write('curr:res {}'.format(self._make_rr_str(resolution)))

    def initiate(self):
        self._write('init')

    def fetch(self):
        val_str = self._query('fetch?')
        if ',' in val_str:
            val = [float(s) for s in val_str.strip('\r\n,').split(',')]
        else:
            val = float(val_str.strip())

        return Q_(val, self._meas_units)

    def read(self):
        """Read current measurement value
        equivalent to sending 'init' and then immediately sending 'fetch?'

        from the manual:
        The READ? command changes the state of the trigger system from the
        “idle” state to the “wait-for-trigger” state. Measurements will begin
        when the specified trigger conditions are satisfied following the receipt
        of the READ? command. Readings are sent immediately to the output
        buffer. You must enter the reading data into your bus controller or the
        multimeter will stop making measurements when the output buffer
        fills. Readings are not stored in the multimeter’s internal memory when
        using the READ? command.
        """
        val_str = self._query('read?')
        if ',' in val_str:
            val = [float(s) for s in val_str.strip('\r\n,').split(',')]
        else:
            val = float(val_str.strip())

        return Q_(val, self._meas_units)

    def trigger(self):
        """Emit the software trigger

        To use this function, the device must be in the 'wait-for-trigger' state and its
        `trigger_source` must be set to 'bus'.
        """
        self._write('*TRG')

    def clear(self):
        self._rsrc.write('\x03')

    @property
    def trigger_source(self):
        src = self._query('trigger:source?')
        return as_enum(TriggerSource, src.rstrip().lower())

    ## not working for some reason, it says TriggerSource object not callable,
    ## thus it isn't recognizing that i'm trying to run the setter

    # @trigger_source.setter
    # @check_enums(src=TriggerSource)
    # def trigger_source(self, src):
    #     self._write('trigger:source {}'.format(src.name))

    @check_enums(src=TriggerSource)
    def set_trigger_source(self, src):
        self._write('trigger:source {}'.format(src.name))

    @property
    def npl_cycles(self):
        func = self._query('func?').strip('\r\n"')
        resp = self._query('{}:nplcycles?'.format(func))
        return float(resp)

    @npl_cycles.setter
    def npl_cycles(self, value):
        if value not in (0.02, 0.2, 1, 10, 100):
            raise ValueError("npl_cycles can only be 0.02, 0.2, 1, 10, or 100")
        func = self._query('func?').strip('\r\n"')
        self._write('{}:nplcycles {}'.format(func, value))
