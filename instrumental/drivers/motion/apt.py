import time

from serial import Serial
from serial.tools.list_ports import comports
from instrumental.drivers.motion import Motion
from instrumental.drivers import ParamSet
from ... import Q_, u

import struct

def list_instruments():
    return [ParamSet(TDC001_APT, port=p.device) for p in comports() if (p.vid, p.pid) == (0x0403, 0xfaf0)]

class APT(Motion):
    """
        Generic class for APT devices.
    """
    def identify(self):
        """Identify the device by libkining its LED"""
        self._ser.write(bytes([0x23, 0x02, 0x00, 0x00, self.dst, self.src]))
    
    def get_info(self):
        self._ser.write(bytes([0x05, 0x00, 0x00, 0x00, self.dst, self.src]))
        rsp = self._ser.read(90)
        return rsp

class TDC001_APT(APT):
    """
        Controlling Thorlabs TDC001 T-Cube DC Servo Motor Controllers using APT commands
    """

    _INST_PARAMS_ = ['serial']
    
    pos_scaling_factor = Q_(1/34304.0, "mm")
    vel_scaling_factor = Q_(1/767367.49, "mm/s")
    acc_scaling_factor = Q_(1/261.93, "mm / s**2")
    
    def _initialize(self):
        self.src = 0x01             # Host controller by default
        self.dst = 0x50             # Generic USB hardware unit
        self._ser = Serial(self._paramset['port'], baudrate=115200, timeout=0.2)
        
    def close(self):
        self._ser.close()
    
    def jog_move(self, direction= 1):
        self._ser.write(bytes([0x6A, 0x04, 0x01, direction, self.dst, self.src]))
        rsp = b""
        while rsp[0:2] != b"\x64\x04":
            rsp = self._ser.read(20)
            time.sleep(0.1)
        return rsp
    
    def get_position(self):
        """ Returns the position of the motor.
        """
        self._ser.write(bytes([0x11, 0x04, 0x01, 0x00, self.dst, self.src]))
        rsp = self._ser.read(12)
        position = struct.unpack('<i', rsp[-4:])[0] * self.pos_scaling_factor
        return position
    
    def get_jog_params(self):
        self._ser.write(bytes([0x17, 0x04, 0x01, 0x00, self.dst, self.src]))
        rsp = self._ser.read(28)
        jog_step_size = struct.unpack('<i', rsp[10:14])[0] * self.pos_scaling_factor
        jog_accel = struct.unpack('<i', rsp[18:22])[0] * self.vel_scaling_factor
        jog_max_accel = struct.unpack('<i', rsp[22:26])[0] * self.acc_scaling_factor
        return jog_step_size, jog_accel, jog_max_accel

    def get_vel_params(self):
        """ Gets the velocity parameters for the specified motor

        Returns
        -------
        (accel: int,
        vel_max: int)
        """
        self._ser.write(bytes([0x14, 0x04, 0x01, 0x00, self.dst, self.src]))
        rsp = self._ser.read(20)
        accel = struct.unpack('<i', rsp[12:16])[0] * self.acc_scaling_factor
        vel_max = struct.unpack('<i', rsp[16:20])[0] * self.vel_scaling_factor
        return accel, vel_max

    def get_enccounter(self):
        """ Gets the encoder count in the controller.
        """
        self._ser.write(bytes([0x0A, 0x04, 0x01, 0x00, self.dst, self.src]))
        rsp = self._ser.read(12)
        enccounter = struct.unpack('<i', rsp[-4:])
        return enccounter

    def home(self):
        """ Homes the device and wait until a move completed
            message is reveiced.
        """
        self._ser.write(bytes([0x43, 0x04, 0x01, 0x00, self.dst, self.src]))
        rsp = b""

        while rsp[0:2] != b"\x44\x04":
            time.sleep(0.2)
            rsp = self._ser.read(6)
