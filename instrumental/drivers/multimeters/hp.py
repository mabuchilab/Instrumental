from enum import Enum
from instrumental import u, Q_
from . import Multimeter
from .. import _get_visa_instrument
from ..util import as_enum, check_enums
from ...errors import InstrumentTypeError

supported_models = ['34401A']


class TriggerSource(Enum):
    bus = 0
    immediate = imm = 1
    ext = 2
    external = 2


def _instrument(params):
    inst = _get_visa_instrument(params)
    idn = inst.query("*IDN?")
    idn_list = idn.split(',')

    if len(idn_list) != 4:
        raise InstrumentTypeError("Not a supported Hewlett-Packard multimeter")
    manufac, model, serial, firmware = idn_list

    if manufac != 'HEWLETT-PACKARD':
        raise InstrumentTypeError("Not a Hewlett-Packard device")
    elif model not in supported_models:
        raise InstrumentTypeError("Not a supported Hewlett-Packard multimeter model")

    return HPMultimeter(visa_inst=inst)


class MultimeterError(Exception):
    pass


class HPMultimeter(Multimeter):
    def __init__(self, visa_inst):
        self.inst = visa_inst
        self.inst.write_termination = '\r\n'
        self._meas_units = None
        self.inst.write('system:remote')
        self.inst.write('trig:count 512')

    def _handle_err_info(self, err_info):
        code, msg = err_info.strip().split(',')
        code = int(code)
        if code != 0:
            raise MultimeterError(msg[1:-1])

    def _query(self, message):
        resp, err_info = self.inst.query(message + ';:syst:err?').split(';')
        self._handle_err_info(err_info)
        return resp

    def _write(self, message):
        err_info = self.inst.query(message + ';:syst:err?')
        self._handle_err_info(err_info)

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

    def config_voltage_dc(self, range=None, resolution=None):
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

    def initiate(self):
        self._write('init')

    def fetch(self):
        val_str = self._query('fetch?')
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
        self.inst.write('\x03')

    @property
    def trigger_source(self):
        src = self._query('trigger:source?')
        return as_enum(TriggerSource, src.rstrip().lower())

    @trigger_source.setter
    @check_enums(src=TriggerSource)
    def trigger_source(self, src):
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
