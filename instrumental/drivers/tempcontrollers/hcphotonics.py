# -*- coding: utf-8 -*-
# Copyright 2014-2017 Dodd Gray, Nate Bogdanowicz
"""
Driver for VISA control of HC Photonics TC038 temperature controller
"""

from __future__ import unicode_literals

from pyvisa.constants import Parity

from . import TempController
from .. import VisaMixin, Facet
from ..util import visa_context
from ...log import get_logger

log = get_logger(__name__)

__all__ = ['TC038']

_INST_PARAMS = ['visa_address']
_INST_CLASSES = ['TC038']


def _check_visa_support(visa_rsrc):
    with visa_context(visa_rsrc, parity=Parity.even, write_termination='\r', read_termination='\r',
                      timeout=50):
        try:
            # This assumes an address of 01
            visa_rsrc.write_raw(b'\x0201010INF6\x03')
            resp = visa_rsrc.read_raw().rstrip()
            assert resp[0:1] == b'\x02'
            assert resp[-1:] == b'\x03'
            assert resp[1:3] == b'01'
            assert resp[3:5] == b'01'
            assert resp[5:7] == b'OK'
            resp[7:-1]
            return 'TC038'
        except Exception as e:
            log.exception(e)
    return None


class TC038(TempController, VisaMixin):
    """HC Photonics TC038 temperature controller"""

    def _initialize(self):
        self._rsrc.parity = Parity.even
        self._rsrc.write_termination = '\r'
        self._rsrc.read_termination = '\r'
        self._address = b'01'

    def _read_response(self):
        resp = self._rsrc.read_raw().rstrip()
        assert resp[0:1] == b'\x02'
        assert resp[-1:] == b'\x03'
        assert resp[1:3] == self._address
        assert resp[3:5] == b'01'
        assert resp[5:7] == b'OK'
        return resp[7:-1]

    def _send_command(self, command, data):
        cpu = 1
        msg = b'\x02%s%02d0%s%s\x03' % (self._address, cpu, command, data)
        self.write_raw(msg)

    def _read_register(self, register):
        """Read one word of data from a D register"""
        data = b'D%04d,01' % register
        self._send_command(b'WRD', data)
        resp = self._read_response()
        assert len(resp) == 4
        return int(resp, base=16)

    def _write_register(self, register, word):
        """Write one word of data to a D register"""
        data = b'D%04d,01,%04X' % (register, word)
        self._send_command(b'WWR', data)
        self._read_response()  # Read OK response

    def _INF(self):
        self._send_command(b'INF', b'6')
        resp = self._read_response()
        assert resp[0] == b'U'
        assert resp[1:5] == b'T150'

        assert resp[8] == b' '
        return resp

    @Facet(units='degC')
    def current_temperature(self):
        return self._read_register(2) / 10.

    @Facet(units='degC', limits=(20,200,0.1))
    def temperature_setpoint(self):
        return self._read_register(3) / 10.

    @temperature_setpoint.setter
    def temperature_setpoint(self, temperature):
        value = int(round(temperature * 10))
        self._write_register(120, value)

    def close(self):
        self._rsrc.close()
