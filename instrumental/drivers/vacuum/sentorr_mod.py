# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
"""
Driver for modified senTorr vacuum ion gauge controllers without builtin RS232. Uses an Arduino Uno
to intercept and relay the status of the front-panel LCDs via serial-over-USB.

The controller uses two MAX7219 LED Display Driver chips, one to drive the 7-segment displays, and
the other to drive the indicator LEDs on the front panel.
"""
import struct
from enum import Enum
import threading
from serial import Serial
from serial.threaded import ReaderThread, Packetizer

from .. import Instrument, ParamSet
from ...errors import Error
from ... import u

_INST_PRIORITY = 9  # There's only one of these devices in existence
_INST_PARAMS = ['port']
_INST_CLASSES = ['SenTorrMod']

TERMINATOR = b'\xfd\x49\xfd\x49'
MSG_GET_ONE = b'\xd3'
MSG_AUTOSEND = b'\xe8'
MSG_NOAUTOSEND = b'\x8e'

err_map = {
    '02 E': 'Pressure burst caused by a sudden rise in pressure at the ion gauge.',
    '03 E': 'No ion current or measurement signal. Possibly a bad connection.',
    '04 E': 'Filament overcurrent caused by a shorted filament current.',
    '05 E': 'Filament undercurrent caused by an open filament; cable not properly connected; bad '
            'control circuit or control circuit not properly installed.',
    '06 E': 'Grid voltage low caused by a grounded grid or a bad grid supply.',
    '07 E': 'Overtemperature caused by a temperature inside unit over 65°C',
    '08 E': 'Board logic failure caused by a bad component or electrical noise.',
    '09 E': 'Overpressure caused by an indicated pressure above high pressure limit of '
            'the ion gauge.',
    '12 E': 'Underpressure caused b y an indicated pressure beyond minimum pressure of ion gauge.',
    '13 E': 'Insufficient current caused b y a dirty cold cathode gauge or an open '
            'cable connection',
    '14 E': 'Invalid keypress caused by a locked keypad.',
}

decode_BCD = {
    0: '0',
    1: '1',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9',
    10: '-',
    11: 'E',
    12: 'H',
    13: 'L',
    14: 'P',
    15: ' '
}

digit_map = {
    0b01111110: '0',
    0b00110000: '1',
    0b01101101: '2',
    0b01111001: '3',
    0b00110011: '4',
    0b01011011: '5',
    0b01011111: '6',
    0b01110000: '7',
    0b01111111: '8',
    0b01111011: '9',
    0b00000001: '-',
    0b01110111: 'A',
    0b01001110: 'C',
    0b01001111: 'E',
    0b01000111: 'F',
    0b00110111: 'H',
    0b00111100: 'J',
    0b00001110: 'L',
    0b01100111: 'P',
    0b00111110: 'U',
    0b00110110: 'X',
    0b00000000: ' ',
}

sign_map = {
    0b00000000: ' ',
    0b00010000: '-',
    0b01110000: '-1',
}

led_map = {
    (5, 120): 'Emis On',
    (5, 0): '',
    (7, 2): '',
}

# The Degas/Emis On/mBar/Torr/Cal/Hyst indicators seem to each be
# driven by 4 LEDs, indicated by the TOP and BOT bitmasks below:
#
# Degas -> D6 TOP
# Emis On -> D6 BOT
# mBar -> D5 TOP
# Torr -> D5 BOT
MASK_TOP = 0b10000111
MASK_BOT = 0b01111000


class Address(Enum):
    """Address codes for each MAX7219 register"""
    NoOp = 0x0
    Digit0 = 0x1
    Digit1 = 0x2
    Digit2 = 0x3
    Digit3 = 0x4
    Digit4 = 0x5
    Digit5 = 0x6
    Digit6 = 0x7
    Digit7 = 0x8
    DecodeMode = 0x9
    Intensity = 0xA
    ScanLimit = 0xB
    Shutdown = 0xC
    DisplayTest = 0xF


class MessagePacketizer(Packetizer):
    TERMINATOR = TERMINATOR
    def __init__(self, gauge):
        Packetizer.__init__(self)
        self.gauge = gauge

    def handle_packet(self, packet):
        if len(packet) != 260:
            return
        self.gauge._update(packet)


class LEDDriver(object):
    """A simple software implementation of a MAX7219"""
    def __init__(self):
        self.registers = {e: 0 for e in Address}
        self.decoders = {}

    def read_message(self, addr, data):
        self.registers[Address(addr)] = data

    def digit(self, digit):
        addr = Address(digit+1)
        bitmask = 1 << digit
        mode = self.registers[Address.DecodeMode]
        reg_val = self.registers[addr]

        if mode & bitmask:
            return decode_BCD[reg_val]
        elif addr in self.decoders:
            return self.decoders[addr](reg_val)
        else:
            return reg_val

    def digits(self):
        return tuple(self.digit(n) for n in range(8))

    @staticmethod
    def decode_digit(reg_val):
        try:
            digit = digit_map[reg_val & 0b01111111]
        except KeyError:
            raise ValueError("Byte code 0b{:08b} does not exist in the digit_map decoder")
        dot = '.' if (reg_val & 0b10000000) else ''
        return digit + dot


class SenTorrMod(Instrument):
    def _initialize(self):
        self._rlock = threading.RLock()
        self._driver_A = LEDDriver()
        self._driver_B = LEDDriver()
        self._driver_A.decoders[Address.Digit0] = LEDDriver.decode_digit
        self._driver_A.decoders[Address.Digit1] = LEDDriver.decode_digit
        self._driver_A.decoders[Address.Digit2] = sign_map.__getitem__
        self._driver_A.decoders[Address.Digit3] = LEDDriver.decode_digit
        self._ser = Serial(self._paramset['port'], timeout=1.0)
        self._thread = None

    def close(self):
        if self._thread:
            self._thread.stop()
        self._ser.close()

    @property
    def autoupdate(self):
        return bool(self._thread)

    @autoupdate.setter
    def autoupdate(self, enable):
        if enable:
            self._enable_autoupdate()
        else:
            self._enable_autoupdate()

    def _enable_autoupdate(self):
        """Create a separate thread to auto-load updates from the device"""
        if self.autoupdate:
            return

        self._thread = ReaderThread(self._ser, lambda: MessagePacketizer(self))
        self._ser.write(MSG_AUTOSEND)
        self._thread.start()

    def _disable_autoupdate(self):
        if not self.autoupdate:
            return

        self._thread.stop()
        self._thread = None
        self._ser.write(MSG_NOAUTOSEND)

    @staticmethod
    def _burst_messages(buf):
        """Yields pairs of message tuples (addr, data) from a buffer"""
        for i in range(0, len(buf), 4):
            addr_B, data_B, addr_A, data_A = struct.unpack_from('>BBBB', buf, i)
            yield ((0x0F & addr_A, data_A),
                   (0x0F & addr_B, data_B))

    def _grab_packet(self):
        """Grab the bytes from the most recent burst packet"""
        self._ser.reset_input_buffer()
        self._ser.write(MSG_GET_ONE)  # Poll the arduino
        msg = self._ser.read(264)
        if msg.endswith(TERMINATOR):
            return msg[:-len(TERMINATOR)]
        raise Error("Received invalid message")

    def update(self):
        """Poll the device for its current state"""
        self._update(self._grab_packet())

    def _update(self, packet):
        with self._rlock:
            for (msg_a, msg_b) in self._burst_messages(packet):
                self._driver_A.read_message(*msg_a)
                self._driver_B.read_message(*msg_b)

    @property
    def pressure(self):
        """The ion gauge's pressure reading"""
        with self._rlock:  # Lock to make sure digits and units match
            digits = self._driver_A.digits()[:4]
            units = self._units()

        try:
            disp = ''.join(digits)
        except TypeError:
            raise Error("Unknown digit values {}".format(digits))

        if disp == '    ':
            raise Error("Must update at least once before reading the pressure")
        elif disp == '0F F':
            raise Error("Ion gauge is off")
        elif disp.endswith('E'):
            raise Error(err_map[disp])

        try:
            mag = float(digits[0] + digits[1] + 'e' + digits[2] + digits[3])
            return mag * units
        except ValueError:
            raise Error("Unknown digit values {}".format(digits))

    def _units(self):
        with self._rlock:
            data = self._driver_B.digit(5)

        mbar_on = bool(data & MASK_TOP)
        torr_on = bool(data & MASK_BOT)
        if mbar_on and torr_on:
            raise Exception("Both mBar and Torr lights are on! Nonsense!")

        if mbar_on:
            return u.mbar
        elif torr_on:
            return u.torr
        else:
            return u.Pa

    @property
    def degas_on(self):
        with self._rlock:
            d6 = self._driver_B.digit(6)
        return bool(d6 & MASK_TOP)


def list_instruments():
    # TODO: This just lists my one Arduino, but it'd be nice to have a better way of
    # IDing these if anyone else ever makes one.
    from serial.tools.list_ports import comports
    return [ParamSet(SenTorrMod, port=p.device) for p in comports()
            if (p.vid, p.pid, p.serial_number) == (0x2A03, 0x0043, '8553130333135141A141')]
