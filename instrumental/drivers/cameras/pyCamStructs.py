# -*- coding: utf-8 -*-
"""
Created on Sat Feb 28 20:26:59 2015

@author: Lab
"""


class PyCamError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def picam_error(error):
    if error == 0:
        return
    else:
        raise(PicamError(error))


def picam_acquisition_error(acquisition_error):
    acquisition_error = acquisition_error.value
    if acquisition_error == 0x0:
        return
    else:
        raise(PicamAcquisitionError(acquisition_error))


class PicamAcquisitionError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        if self.value == 0x0:
            return "No error occured"
        elif self.value == 0x1:
            return "DataLost"
        elif self.value == 0x2:
            return "ConnectionLost"
        else:
            return "An unkown error with code {}".format(self.value)


class PicamError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return error_type(self.value)


def error_type(error):
    if error == 0:
        return "No Error Occured"
    elif error == 4:
        return "UnexpectedError"
    elif error == 3:
        return "UnexpectedNullPointer"
    elif error == 35:
        return "InvalidPointer"
    elif error == 39:
        return "InvalidCount"
    elif error == 42:
        return "InvalidOperation"
    elif error == 43:
        return "OperationCanceled"
    elif error == 1:
        return "LibraryNotInitialized"
    elif error == 5:
        return "LibraryAlreadyInitialized"
    elif error == 16:
        return "InvalidEnumeratedType"
    elif error == 17:
        return "EnumerationValueNotDefined"
    elif error == 18:
        return "NotDiscoveringCameras"
    elif error == 19:
        return "AlreadyDiscoveringCameras"
    elif error == 34:
        return "NoCamerasAvailable"
    elif error == 7:
        return "CameraAlreadyOpened"
    elif error == 8:
        return "InvalidCameraID"
    elif error == 9:
        return "InvalidHandle"
    elif error == 15:
        return "DeviceCommunicationFailed"
    elif error == 23:
        return "DeviceDisconnected"
    elif error == 24:
        return "DeviceOpenElsewhere"
    elif error == 6:
        return "InvalidDemoModel"
    elif error == 21:
        return "InvalidDemoSerialNumber"
    elif error == 22:
        return "DemoAlreadyConnected"
    elif error == 40:
        return "DemoNotSupported"
    elif error == 11:
        return "ParameterHasInvalidValueType"
    elif error == 13:
        return "ParameterHasInvalidConstraintType"
    elif error == 12:
        return "ParameterDoesNotExist"
    elif error == 10:
        return "ParameterValueIsReadOnly"
    elif error == 2:
        return "InvalidParameterValue"
    elif error == 38:
        return "InvalidConstraintCategory"
    elif error == 14:
        return "ParameterValueIsIrrelevant"
    elif error == 25:
        return "ParameterIsNotOnlineable"
    elif error == 26:
        return "ParameterIsNotReadable"
    elif error == 28:
        return "InvalidParameterValues"
    elif error == 29:
        return "ParametersNotCommitted"
    elif error == 30:
        return "InvalidAcquisitionBuffer"
    elif error == 36:
        return "InvalidReadoutCount"
    elif error == 37:
        return "InvalidReadoutTimeOut"
    elif error == 31:
        return "InsufficientMemory"
    elif error == 20:
        return "AcquisitionInProgress"
    elif error == 27:
        return "AcquisitionNotInProgress"
    elif error == 32:
        return "TimeOutOccurred"
    elif error == 33:
        return "AcquisitionUpdatedHandlerRegistered"
    elif error == 41:
        return "NondestructiveReadoutEnabled"
    else:
        return error
