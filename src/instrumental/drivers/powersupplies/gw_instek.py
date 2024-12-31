# -*- coding: utf-8  -*-
"""
Driver for GW Instek
"""

from . import PowerSupply
from .. import VisaMixin, Facet
from ... import Q_


class GPD_3303S(PowerSupply, VisaMixin):
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('GW INSTEK', ['GPD-3303S'])
    
    baud_list = [115200, 57600, 9600]
 
    def _initialize(self):
        self._rsrc.write_termination = '\n'
        self._rsrc.read_termination = '\n'

    def get_voltage(self, channel):
        channel = int(channel)
        if int(channel) not in [1, 2]:
            raise ValueError('channel must be 1 or 2')
        return Q_(self.query('VSET%i?' % channel))

    def set_voltage(self, channel, voltage):
        channel = int(channel)
        if int(channel) not in [1, 2]:
            raise ValueError('channel must be 1 or 2')
        query = 'VSET%i:%.3f' % (channel, voltage) 
        self.write(query)
    
    def get_current(self, channel):
        channel = int(channel)
        if int(channel) not in [1, 2]:
            raise ValueError('channel must be 1 or 2')
        return Q_(self.query('ISET%i?' % channel))

    def set_current(self, channel, current):
        channel = int(channel)
        if int(channel) not in [1, 2]:
            raise ValueError('channel must be 1 or 2')
        self.write('ISET%i:%f' % (channel, current))    

    @Facet(units='V')
    def voltage1(self):
        return self.get_voltage(1)

    @voltage1.setter
    def voltage1(self, voltage):
        self.set_voltage(1, voltage)

    @Facet(units='V')
    def voltage2(self):
        return self.get_voltage(2)

    @voltage2.setter
    def voltage2(self, voltage):
        self.set_voltage(2, voltage)
    
    @Facet(units='A')
    def current1(self):
        return self.get_current(1)    
    
    @current1.setter
    def current1(self, current):
        self.set_current(1, current)

    @Facet(units='A')
    def current2(self):
        return self.get_current(2)
    
    @current2.setter
    def current2(self, current):
        self.set_current(2, current)

    @Facet(type=bool)
    def output(self):
        status = self.query('STATUS?')
        return int(status[1])

    @output.setter
    def output(self, on):
        on = int(on)
        self.write('OUT%i' % on)
    
    @Facet(units='bps')
    def baud(self):
        status = self.query('STATUS?')
        return self.baud_list[int(status[6:8],2)]

    @Facet(type=bool)
    def beep(self):
        status = self.query('STATUS?')
        return int(status[4])

    @beep.setter
    def beep(self, beep):
        beep = int(beep)
        self.write('BEEP%i' % beep)

    def close(self):
        self._rsrc.close()
