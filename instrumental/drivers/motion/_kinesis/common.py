from enum import Enum


# Message Enums
#
class MessageType(Enum):
    GenericDevice = 0
    GenericPiezo = 1
    GenericMotor = 2
    GenericDCMotor = 3
    GenericSimpleMotor = 4
    RackDevice = 5
    Laser = 6
    TECCtlr = 7
    Quad = 8
    NanoTrak = 9
    Specialized = 10
    Solenoid = 11


class GenericDevice(Enum):
    SettingsInitialized = 0
    SettingsUpdated = 1
    Error = 2
    Close = 3


class GenericMotor(Enum):
    Homed = 0
    Moved = 1
    Stopped = 2
    LimitUpdated = 3


class GenericDCMotor(Enum):
    Error = 0
    Status = 1


MessageIDs = {
    MessageType.GenericDevice: GenericDevice,
    MessageType.GenericMotor: GenericMotor,
    MessageType.GenericDCMotor: GenericDCMotor
}


class KinesisError(Exception):
    messages = {
        0: 'Success',
        1: 'The FTDI functions have not been initialized',
        2: 'The device could not be found. Make sure to call TLI_BuildDeviceList().',
        3: 'The device must be opened before it can be accessed',
        4: 'An I/O Error has occured in the FTDI chip',
        5: 'There are insufficient resources to run this application',
        6: 'An invalid parameter has been supplied to the device',
        7: 'The device is no longer present',
        8: 'The device detected does not match that expected',
        32: 'The device is already open',
        33: 'The device has stopped responding',
        34: 'This function has not been implemented',
        35: 'The device has reported a fault',
        36: 'The function could not be completed because the device is disconnected',
        41: 'The firmware has thrown an error',
        42: 'The device has failed to initialize',
        43: 'An invalid channel address was supplied',
        37: 'The device cannot perform this function until it has been Homed',
        38: 'The function cannot be performed as it would result in an illegal position',
        39: 'An invalid velocity parameter was supplied. The velocity must be greater than zero',
        44: 'This device does not support Homing. Check the Limit switch parameters are correct',
        45: 'An invalid jog mode was supplied for the jog function',
    }

    def __init__(self, code=None, msg=''):
        if code is not None and not msg:
            msg = '(0x{:X}) {}'.format(code, self.messages[code])
        super(KinesisError, self).__init__(msg)
        self.code = code
