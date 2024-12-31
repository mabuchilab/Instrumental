# -*- coding: utf-8 -*-
# Copyright 2015-2021 Christopher Rogers, Nate Bogdanowicz
from future.utils import PY2

import time
from warnings import warn

import numpy as np
from enum import IntEnum
from nicelib import NiceLib, load_lib, RetHandler, ret_ignore, Sig, NiceObject

from . import Camera
from .. import ParamSet, register_cleanup
from ..util import check_units, check_enums
from ...errors import Error, InstrumentNotFoundError, TimeoutError
from ...log import get_logger
from ... import Q_

log = get_logger(__name__)

# could not find an equivalent in the future module, so I don't knwow what that buffer is??
if PY2:
    memoryview = buffer  # Needed b/c np.frombuffer is broken on memoryviews in PY2


class PicamError(Error):
    def __init__(self, msg, code=None):
        super(Error, self).__init__(msg)
        self.msg = msg
        self.code = code


lib = load_lib('picam', __package__)
BYTES_PER_PIXEL = 2


@RetHandler(num_retvals=0)
def ret_error(error):
    if error != 0:
        code = PicamEnums.Error(error)

        if bool(NicePicamLib.IsLibraryInitialized()):
            msg = NicePicamLib.GetEnumerationString(lib.PicamEnumeratedType_Error, error).decode()
            raise PicamError(msg, code)
        else:
            ret_enum_string_error.__func__(error)


@RetHandler(num_retvals=0)
def ret_enum_string_error(error):
    if error != 0:
        code = PicamEnums.Error(error)

        if error == lib.PicamError_LibraryNotInitialized:
            msg = 'Library not initialized'
        if error == lib.PicamError_InvalidEnumeratedType:
            msg = 'Invalid enumerated Type'
        if error == lib.PicamError_EnumerationValueNotDefined:
            msg = 'Enumeration value not defined.'
        else:
            msg = 'Error when getting enumeration string. Error code {}'.format(code.name)

        raise PicamError(msg, code)


class NicePicamLib(NiceLib):
    """Wrapper for Picam.dll"""
    _info_ = lib
    _buflen_ = 256
    _prefix_ = 'Picam_'
    _ret_ = ret_error

    GetVersion = Sig('out', 'out', 'out', 'out')
    IsLibraryInitialized = Sig('out', ret=ret_ignore)
    InitializeLibrary = Sig()
    UninitializeLibrary = Sig()
    DestroyString = Sig('in')
    # GetEnumerationString = Sig('in', 'in', 'bufout', ret=ret_ignore)
    GetEnumerationString = Sig('in', 'in', 'bufout', ret=ret_enum_string_error)
    DestroyCameraIDs = Sig('in')
    GetAvailableCameraIDs = Sig('out', 'out')
    GetUnavailableCameraIDs = Sig('out', 'out')
    IsCameraIDConnected = Sig('in', 'out')
    IsCameraIDOpenElsewhere = Sig('in', 'out')
    DestroyHandles = Sig('in')
    OpenFirstCamera = Sig('out')
    OpenCamera = Sig('in', 'out')
    # DestroyFirmwareDetails = Sig(firmware_array)
    DestroyFirmwareDetails = Sig('in')
    # DestroyModels = Sig(model_array)
    DestroyModels = Sig('in')
    GetAvailableDemoCameraModels = Sig('out', 'out')
    ConnectDemoCamera = Sig('in', 'in', 'out')
    DisconnectDemoCamera = Sig('in')
    GetOpenCameras = Sig('out', 'out')
    IsDemoCamera = Sig('in', 'out')
    # GetFirmwareDetails = Sig(id, firmware_array, firmware_count)
    GetFirmwareDetails = Sig('in', 'out', 'out')
    # DestroyRois = Sig(rois)
    DestroyRois = Sig('in')
    # DestroyModulations = Sig(modulations)
    DestroyModulations = Sig('in')
    # DestroyPulses = Sig(pulses)
    DestroyPulses = Sig('in')
    # DestroyParameters = Sig(parameter_array)
    DestroyParameters = Sig('in')
    # DestroyCollectionConstraints = Sig(constraint_array)
    DestroyCollectionConstraints = Sig('in')
    # DestroyRangeConstraints = Sig(constraint_array)
    DestroyRangeConstraints = Sig('in')
    # DestroyRoisConstraints = Sig(constraint_array)
    DestroyRoisConstraints = Sig('in')
    # DestroyModulationsConstraints = Sig(constraint_array)
    DestroyModulationsConstraints = Sig('in')
    # DestroyPulseConstraints = Sig(constraint_array)
    DestroyPulseConstraints = Sig('in')

    class Camera(NiceObject):
        _init_ = 'OpenCamera'

        CloseCamera = Sig('in')
        IsCameraConnected = Sig('in', 'out')
        GetCameraID = Sig('in', 'out')
        #GetParameterIntegerValue = Sig(camera, parameter, value)
        GetParameterIntegerValue = Sig('in', 'in', 'out')
        #SetParameterIntegerValue = Sig(camera, parameter, value)
        SetParameterIntegerValue = Sig('in', 'in', 'in')
        #CanSetParameterIntegerValue = Sig(camera, parameter, value, settable)
        CanSetParameterIntegerValue = Sig('in', 'in', 'in', 'out')
        #GetParameterLargeIntegerValue = Sig(camera, parameter, value)
        GetParameterLargeIntegerValue = Sig('in', 'in', 'out')
        #SetParameterLargeIntegerValue = Sig(camera, parameter, value)
        SetParameterLargeIntegerValue = Sig('in', 'in', 'in')
        #CanSetParameterLargeIntegerValue = Sig(camera, parameter, value, settable)
        CanSetParameterLargeIntegerValue = Sig('in', 'in', 'in', 'out')
        #GetParameterFloatingPointValue = Sig(camera, parameter, value)
        GetParameterFloatingPointValue = Sig('in', 'in', 'out')
        #SetParameterFloatingPointValue = Sig(camera, parameter, value)
        SetParameterFloatingPointValue = Sig('in', 'in', 'in')
        #CanSetParameterFloatingPointValue = Sig(camera, parameter, value, settable)
        CanSetParameterFloatingPointValue = Sig('in', 'in', 'in', 'out')
        #GetParameterRoisValue = Sig(camera, parameter, value)
        GetParameterRoisValue = Sig('in', 'in', 'out')
        #SetParameterRoisValue = Sig(camera, parameter, value)
        SetParameterRoisValue = Sig('in', 'in', 'in')
        #CanSetParameterRoisValue = Sig(camera, parameter, value, settable)
        CanSetParameterRoisValue = Sig('in', 'in', 'in', 'out')
        #GetParameterPulseValue = Sig(camera, parameter, value)
        GetParameterPulseValue = Sig('in', 'in', 'out')
        #SetParameterPulseValue = Sig(camera, parameter, value)
        SetParameterPulseValue = Sig('in', 'in', 'in')
        #CanSetParameterPulseValue = Sig(camera, parameter, value, settable)
        CanSetParameterPulseValue = Sig('in', 'in', 'in', 'out')
        #GetParameterModulationsValue = Sig(camera, parameter, value)
        GetParameterModulationsValue = Sig('in', 'in', 'out')
        #SetParameterModulationsValue = Sig(camera, parameter, value)
        SetParameterModulationsValue = Sig('in', 'in', 'in')
        #CanSetParameterModulationsValue = Sig(camera, parameter, value, settable)
        CanSetParameterModulationsValue = Sig('in', 'in', 'in', 'out')
        #GetParameterIntegerDefaultValue = Sig(camera, parameter, value)
        GetParameterIntegerDefaultValue = Sig('in', 'in', 'out')
        #GetParameterLargeIntegerDefaultValue = Sig(camera, parameter, value)
        GetParameterLargeIntegerDefaultValue = Sig('in', 'in', 'out')
        #GetParameterFloatingPointDefaultValue = Sig(camera, parameter, value)
        GetParameterFloatingPointDefaultValue = Sig('in', 'in', 'out')
        #GetParameterRoisDefaultValue = Sig(camera, parameter, value)
        GetParameterRoisDefaultValue = Sig('in', 'in', 'out')
        #GetParameterPulseDefaultValue = Sig(camera, parameter, value)
        GetParameterPulseDefaultValue = Sig('in', 'in', 'out')
        #GetParameterModulationsDefaultValue = Sig(camera, parameter, value)
        GetParameterModulationsDefaultValue = Sig('in', 'in', 'out')
        #CanSetParameterOnline = Sig(camera, parameter, onlineable)
        CanSetParameterOnline = Sig('in', 'in', 'out')
        #SetParameterIntegerValueOnline = Sig(camera, parameter, value)
        SetParameterIntegerValueOnline = Sig('in', 'in', 'in')
        #SetParameterFloatingPointValueOnline = Sig(camera, parameter, value)

        SetParameterFloatingPointValueOnline = Sig('in', 'in', 'in')
        #SetParameterPulseValueOnline = Sig(camera, parameter, value)
        SetParameterPulseValueOnline = Sig('in', 'in', 'in')
        #CanReadParameter = Sig(camera, parameter, readable)
        CanReadParameter = Sig('in', 'in', 'out')
        #ReadParameterIntegerValue = Sig(camera, parameter, value)
        ReadParameterIntegerValue = Sig('in', 'in', 'out')
        #ReadParameterFloatingPointValue = Sig(camera, parameter, value)
        ReadParameterFloatingPointValue = Sig('in', 'in', 'out')
        #GetParameters = Sig(camera, parameter_array, parameter_count)
        GetParameters = Sig('in', 'out', 'out')
        #DoesParameterExist = Sig(camera, parameter, exists)
        DoesParameterExist = Sig('in', 'in', 'out')
        #IsParameterRelevant = Sig(camera, parameter, relevant)
        IsParameterRelevant = Sig('in', 'in', 'out')
        #GetParameterValueType = Sig(camera, parameter, type)
        GetParameterValueType = Sig('in', 'in', 'out')
        #GetParameterEnumeratedType = Sig(camera, parameter, type)
        GetParameterEnumeratedType = Sig('in', 'in', 'out')
        #GetParameterValueAccess = Sig(camera, parameter, access)
        GetParameterValueAccess = Sig('in', 'in', 'out')
        #GetParameterConstraintType = Sig(camera, parameter, type)
        GetParameterConstraintType = Sig('in', 'in', 'out')
        #GetParameterCollectionConstraint = Sig(camera, parameter, category, constraint)
        GetParameterCollectionConstraint = Sig('in', 'in', 'in', 'out')
        #GetParameterRangeConstraint = Sig(camera, parameter, category, constraint)
        GetParameterRangeConstraint = Sig('in', 'in', 'in', 'out')
        #GetParameterRoisConstraint = Sig(camera, parameter, category, constraint)
        GetParameterRoisConstraint = Sig('in', 'in', 'in', 'out')
        #GetParameterPulseConstraint = Sig(camera, parameter, category, constraint)
        GetParameterPulseConstraint = Sig('in', 'in', 'in', 'out')
        #GetParameterModulationsConstraint = Sig(camera, parameter, category, constraint)
        GetParameterModulationsConstraint = Sig('in', 'in', 'in', 'out')
        #AreParametersCommitted = Sig(camera, committed)
        AreParametersCommitted = Sig('in', 'out')
        #CommitParameters = Sig(camera, failed_parameter_array, failed_parameter_count)
        CommitParameters = Sig('in', 'out', 'out', ret=ret_ignore)
        #Acquire = Sig(camera, readout_count, readout_time_out, available, errors)
        Acquire = Sig('in', 'in', 'in', 'out', 'out')
        #StartAcquisition = Sig(camera)
        StartAcquisition = Sig('in')
        #StopAcquisition = Sig(camera)
        StopAcquisition = Sig('in')
        #IsAcquisitionRunning = Sig(camera, running)
        IsAcquisitionRunning = Sig('in', 'out')
        #WaitForAcquisitionUpdate = Sig(camera, readout_time_out, available, status)
        WaitForAcquisitionUpdate = Sig('in', 'in', 'out', 'out')


ffi = NicePicamLib._ffi
ffilib = NicePicamLib._ffilib


def _c_data_to_numpy(address, size, dtype=float):
    """Creates a numpy array from a C array at ``address`` with ``size`` bytes.

    Does *not* copy the data.
    """
    image_buf = memoryview(ffi.buffer(address, size))
    return np.frombuffer(image_buf, dtype)


class EnumTypes(object):
    """ Class containg the enumerations in Picam.dll"""
    def __init__(self):
        enum_type_dict = self._get_enum_dict()
        for enum_type, enum in enum_type_dict.items():
            self.__dict__[enum_type] = enum

    def _get_enum_dict(self):
        lib_dict = NicePicamLib._ffilib.__dict__
        enum_type_dict = {}
        for enum, value in lib_dict.items():
            if isinstance(value, int):
                enum_type, enum_name = enum.split('_', 1)
                if enum_type[0:5] == 'Picam':
                    enum_type = enum_type[5:]
                if enum_type == '':
                    enum_type_dict[enum_name] = value
                else:
                    if enum_type not in enum_type_dict:
                        enum_type_dict[enum_type] = {}
                    enum_type_dict[enum_type][enum_name] = value
        for enum_type, enum_dict in enum_type_dict.items():
            if isinstance(enum_dict, dict):
                enum_type_dict[enum_type] = IntEnum(enum_type, enum_dict)
        return enum_type_dict


#: Namespace of all the enums in the Picam SDK
PicamEnums = EnumTypes()


#class PicamAcquisitionError(PicamError):
#    def __init__(self, value):
#        self.value = value
#
#    def __str__(self):
#        if self.value == NicePicamLib._ffilib.PicamAcquisitionErrorsMask_None:
#            return "No error occured"
#        elif self.value == NicePicamLib._ffilib.PicamAcquisitionErrorsMask_DataLost:
#            return "DataLost"
#        elif self.value == NicePicamLib._ffilib.PicamAcquisitionErrorsMask_ConnectionLost:
#            return "ConnectionLost"
#        else:
#            return "An unkown error with code {}".format(self.value)


# Destroyable data:
#   The idea for any destroyable data is to immediately pass it through `ffi.gc()` to get a
# reference-counting owner of the data. In some cases that data is an *array* of items. In this
# case, each item-wrapping object we create must hold a reference to the parent array to prevent its
# cleanup.

def struct_property(name):
    def fget(self):
        return getattr(self._struct_ptr, name)

    def fset(self, value):
        setattr(self._struct_ptr, name, value)

    return property(fget, fset)


# Used to ignore errors encountered when calling the Destroy functions, which usually happen because
# the library has already been uninitialized.
def ignore_error(func):
    def wrapped(*args, **kwds):
        try:
            func(*args, **kwds)
        except Exception as e:
            log.info('Ignoring error "%s"', e)
    return wrapped


class PicamPulse(object):
    def __init__(self, pulse_ptr):
        self._struct_ptr = pulse_ptr

    def __repr__(self):
        return f'PicamPulse({self.delay=}, {self.width=})'

    delay = struct_property('delay')
    width = struct_property('width')


class PicamRois(object):
    """List-like group of `PicamRoi` objects

    Supports index-based access, e.g. ``roi = rois[0]``.
    """
    def __init__(self, rois_ptr):
        self._ptr = rois_ptr
        self._rois = [PicamRoi(self, rois_ptr.roi_array[i]) for i in range(rois_ptr.roi_count)]

    def __repr__(self):
        rois = ', '.join(repr(roi) for roi in self._rois)
        return f'PicamRois([{rois}])'

    def __getitem__(self, index):
        return self._rois[index]

    def __len__(self):
        return len(self._rois)


class PicamRoi(object):
    def __init__(self, parent, item_ptr):
        self._parent_ref = parent  # Keep a ref to prevent collection
        self._struct_ptr = item_ptr

    def __repr__(self):
        return (f'PicamRoi({self.x=}, {self.y=}, {self.width=}, {self.height=}, '
                f'{self.x_binning=}, {self.y_binning=})')

    x = struct_property('x')
    y = struct_property('y')
    x_binning = struct_property('x_binning')
    y_binning = struct_property('y_binning')
    width = struct_property('width')
    height = struct_property('height')


class PicamModulations(object):
    """List-like group of `PicamModulation` objects

    Supports index-based access, e.g. ``mod = mods[0]``.
    """
    def __init__(self, mods_ptr):
        self._ptr = mods_ptr
        self._mods = [PicamModulation(self, mods_ptr.modulation_array[i])
                      for i in range(mods_ptr.modulation_count)]

    def __repr__(self):
        mods = ', '.join(repr(mod) for mod in self._mods)
        return f'PicamModulations([{mods}])'

    def __getitem__(self, index):
        return self._mods[index]

    def __len__(self):
        return len(self._mods)


class PicamModulation(object):
    def __init__(self, parent, item_ptr):
        self._parent_ref = parent  # Keep a ref to prevent collection
        self._struct_ptr = item_ptr

    def __repr__(self):
        return (f'PicamModulation({self.duration=}, {self.frequency=}, {self.phase=}, '
                f'{self.output_signal_frequency=})')

    duration = struct_property('duration')
    frequency = struct_property('frequency')
    phase = struct_property('phase')
    output_signal_frequency = struct_property('output_signal_frequency')


class PicamCameraID(object):
    """Picam CameraID"""
    def __init__(self, base_ptr, index):
        self._base_ptr = base_ptr  # Keep a ref to prevent collection
        self._struct_ptr = base_ptr[index]

    @classmethod
    def from_array(cls, id_array, count):
        id_array = ffi.gc(id_array, ignore_error(NicePicamLib.DestroyCameraIDs))
        return [cls(id_array, i) for i in range(count)]

    def __repr__(self):
        return f'<PicamCameraID({self.model=}, {self.serial_number=})>'

    def to_params(self):
        """Get an instrumental ParamSet describing this PicamCameraID"""
        is_demo = bool(NicePicamLib.IsDemoCamera(self._struct_ptr))
        return ParamSet(
            PicamCamera,
            serial=self.serial_number,
            model=self.model.name,
            is_demo=is_demo,
        )

    @property
    def computer_interface(self):
        return PicamEnums.ComputerInterface(self._struct_ptr.computer_interface)

    @property
    def model(self):
        return PicamEnums.Model(self._struct_ptr.model)

    @property
    def sensor_name(self):
        return ffi.string(self._struct_ptr.sensor_name)

    @property
    def serial_number(self):
        return ffi.string(self._struct_ptr.serial_number)


def list_instruments():
    cam_ids = sdk.get_available_camera_IDs()
    return [cam_id.to_params() for cam_id in cam_ids]


def _find_camera_id(paramset):
    """Find camera_id from a paramset, connecting a demo camera if its missing"""
    # NOTE this currently isn't that useful due to the way instrumental.instrument() looks for
    # cameras. It directly calls list_instruments() and searches the results. We might consider
    # changing that function, though saving a demo camera does seem like a pretty unusual case,
    # practically speaking.
    try:
        return _find_attached_camera_id(paramset)
    except InstrumentNotFoundError:
        if not (paramset.get('is_demo') and 'model' in paramset and 'serial' in paramset):
            raise

    model_enum = PicamEnums.Model[paramset['model']]
    sdk.connect_demo_camera(model_enum, paramset['serial'])
    return _find_attached_camera_id(paramset)


def _find_attached_camera_id(paramset):
    cam_ids = sdk.get_available_camera_IDs()
    if not cam_ids:
        raise InstrumentNotFoundError("No cameras attached")

    for cam_id in cam_ids:
        cam_params = cam_id.to_params()
        if paramset.matches(cam_params):
            return cam_id

    raise InstrumentNotFoundError("No camera found matching the given parameters")


class Parameter(object):
    """Base class for Picam Parameters"""
    def __init__(self, dev : NicePicamLib.Camera, parameter):
        self._dev = dev
        self._param = parameter

    @staticmethod
    def create(dev, parameter):
        VT = PicamEnums.ValueType
        ptype = PicamEnums.ValueType(dev.GetParameterValueType(parameter))
        return {
            VT.Integer: IntegerParameter,
            VT.Boolean: BooleanParameter,
            VT.Enumeration: EnumerationParameter,
            VT.LargeInteger: LargeIntegerParameter,
            VT.FloatingPoint: FloatingPointParameter,
            VT.Rois: RoisParameter,
            VT.Pulse: PulseParameter,
            VT.Modulations: ModulationsParameter,
        }[ptype](dev, parameter)


class ModulationsParameter(Parameter):
    def get_value(self) -> PicamModulations:
        _ptr = self._dev.GetParameterModulationsValue(self._param)
        ptr = ffi.gc(_ptr, ignore_error(NicePicamLib.DestroyModulations))
        return PicamModulations(ptr)

    def set_value(self, value: PicamModulations):
        self._dev.SetParameterModulationsValue(self._param, value._ptr)

    def can_set(self, value: PicamModulations) -> bool:
        return bool(self._dev.CanSetParameterModulationsValue(self._param, value._ptr))

    def get_default(self) -> PicamModulations:
        _ptr = self._dev.GetParameterModulationsDefaultValue(self._param)
        ptr = ffi.gc(_ptr, ignore_error(NicePicamLib.DestroyModulations))
        return PicamModulations(ptr)


class PulseParameter(Parameter):
    def get_value(self) -> PicamPulse:
        _ptr = self._dev.GetParameterPulseValue(self._param)
        ptr = ffi.gc(_ptr, ignore_error(NicePicamLib.DestroyPulses))
        return PicamPulse(ptr)

    def set_value(self, value: PicamPulse):
        self._dev.SetParameterPulseValue(self._param, value._struct_ptr)

    def can_set(self, value: PicamPulse) -> bool:
        return bool(self._dev.CanSetParameterPulseValue(self._param, value._struct_ptr))

    def get_default(self) -> PicamPulse:
        _ptr = self._dev.GetParameterPulseDefaultValue(self._param)
        ptr = ffi.gc(_ptr, ignore_error(NicePicamLib.DestroyPulses))
        return PicamPulse(ptr)


class RoisParameter(Parameter):
    def get_value(self) -> PicamRois:
        _ptr = self._dev.GetParameterRoisValue(self._param)
        ptr = ffi.gc(_ptr, ignore_error(NicePicamLib.DestroyRois))
        return PicamRois(ptr)

    def set_value(self, value: PicamRois):
        self._dev.SetParameterRoisValue(self._param, value._ptr)

    def can_set(self, value: PicamRois) -> bool:
        return bool(self._dev.CanSetParameterRoisValue(self._param, value._ptr))

    def get_default(self) -> PicamRois:
        _ptr = self._dev.GetParameterRoisDefaultValue(self._param)
        ptr = ffi.gc(_ptr, ignore_error(NicePicamLib.DestroyRois))
        return PicamRois(ptr)


class FloatingPointParameter(Parameter):
    def get_value(self) -> float:
        return self._dev.GetParameterFloatingPointValue(self._param)

    def set_value(self, value: float):
        self._dev.SetParameterFloatingPointValue(self._param, value)

    def can_set(self, value: float) -> bool:
        return bool(self._dev.CanSetParameterFloatingPointValue(self._param, value))

    def get_default(self) -> float:
        return self._dev.GetParameterFloatingPointDefaultValue(self._param)


class LargeIntegerParameter(Parameter):
    def get_value(self) -> int:
        return self._dev.GetParameterLargeIntegerValue(self._param)

    def set_value(self, value: int):
        self._dev.SetParameterLargeIntegerValue(self._param, value)

    def can_set(self, value: int) -> bool:
        return bool(self._dev.CanSetParameterLargeIntegerValue(self._param, value))

    def get_default(self) -> int:
        return self._dev.GetParameterLargeIntegerDefaultValue(self._param)


class IntegerParameter(Parameter):
    def get_value(self) -> int:
        return self._dev.GetParameterIntegerValue(self._param)

    def set_value(self, value: int):
        self._dev.SetParameterIntegerValue(self._param, value)

    def can_set(self, value: int) -> bool:
        return bool(self._dev.CanSetParameterIntegerValue(self._param, value))

    def get_default(self) -> int:
        return self._dev.GetParameterIntegerDefaultValue(self._param)


class BooleanParameter(IntegerParameter):
    def get_value(self):
        return bool(super().get_value())

    def get_default(self):
        return bool(super().get_default())


class EnumerationParameter(IntegerParameter):
    def __init__(self, dev, parameter):
        super().__init__(dev, parameter)
        etype = PicamEnums.EnumeratedType(self._dev.GetParameterEnumeratedType(self._param))
        self._enumtype = getattr(PicamEnums, etype.name)

    def get_value(self):
        return self._enumtype(super().get_value())

    def get_default_value(self):
        return self._enumtype(super().get_default())


class Parameters(object):
    """Class to namespace Parameters"""
    def __init__(self, parameters: dict[str, Parameter]):
        self.parameters = parameters
        for name, value in parameters.items():
            setattr(self, name, value)


class Timer(object):
    def __init__(self, timeout):
        self._end_time = None if (timeout is None) else (time.time() + timeout)

    def time_left(self):
        if self._end_time is None:
            return -1
        time_left = self._end_time - time.time()
        return max(0, time_left)

    def time_left_ms(self):
        if self._end_time is None:
            return -1
        time_left = (self._end_time - time.time()) * 1000
        return max(0, time_left)


class PicamCamera(Camera):
    """ A Picam Camera """
    _INST_PARAMS_ = ['serial', 'model']

    _NicePicamLib = NicePicamLib
    _NicePicam = NicePicamLib.Camera
    _ffi = NicePicamLib._ffi
    _ffilib = NicePicamLib._ffilib

    def _initialize(self):
        cam_id = _find_camera_id(self._paramset)
        self._dev = NicePicamLib.Camera(cam_id._struct_ptr)
        self._create_params()
        self._latest_available_data = None

    def _create_params(self):
        _params = {}
        for p in PicamEnums.Parameter:
            try:
                _params[p.name] = Parameter.create(self._dev, p)
            except PicamError as e:
                pass

        #: Parameters of the camera
        self.params = Parameters(_params)

    def close(self):
        log.info('Closing Picam camera...')
        self._dev.CloseCamera()

    #
    # Generic Camera interface
    @property
    def width(self):
        self._get_rois()[0].width

    @property
    def height(self):
        self._get_rois()[0].height

    @property
    def max_width(self):
        return self._get_rois_constraint().width_constraint.maximum

    @property
    def max_height(self):
        return self._get_rois_constraint().height_constraint.maximum

    def start_capture(self, **kwds):
        self._handle_kwds(kwds)

        self.set_roi(x=int(kwds['left']), y=int(kwds['top']),
                     width=int(kwds['width']), height=int(kwds['height']),
                     x_binning=kwds['hbin'], y_binning=kwds['vbin'])
        self.params.ReadoutCount.set_value(kwds['n_frames'])
        self.params.ExposureTime.set_value(int(kwds['exposure_time'].m_as('ms')))

        self.commit_parameters()
        self._dev.StartAcquisition()

    @check_units(timeout='?ms')
    def get_captured_image(self, timeout='1s', copy=True):
        timer = Timer(Q_(timeout).m_as('s'))

        error = None
        readouts = []
        running = True

        # Per the Picam API docs, we must call WaitForAcquisitionUpdate until status.running is
        # False. If there's an error, we StopAcquisition and continue reading until finished.
        while running:
            timeout_ms = int(timer.time_left_ms())

            try:
                available_data, status = self._dev.WaitForAcquisitionUpdate(timeout_ms)
            except PicamError as e:
                error = e
                self._dev.StopAcquisition()
            else:
                running = status.running
                if available_data.readout_count > 0:
                    readouts.extend(self._extract_available_data(available_data, copy))

        if error:
            if error.code == PicamEnums.Error.TimeOutOccurred:
                raise TimeoutError("Timed out while waiting for image readout")
            else:
                raise error

        # For our standard API, only return first frame and ROI
        if len(readouts) == 1:
            return readouts[0][0][0]
        else:
            return tuple(ro[0][0] for ro in readouts)

    def grab_image(self, timeout='1s', copy=True, **kwds):
        self.start_capture(**kwds)
        return self.get_captured_image(timeout=timeout, copy=copy)

    def start_live_video(self, **kwds):
        kwds['n_frames'] = 0
        self.start_capture(**kwds)

    def stop_live_video(self):
        self._dev.StopAcquisition()

        running = True
        while running:
            _, status = self._dev.WaitForAcquisitionUpdate(-1)
            running = status.running

    @check_units(timeout='?ms')
    def wait_for_frame(self, timeout=None):
        timeout_ms = -1 if timeout is None else Q_(timeout).m_as('ms')
        try:
            self._latest_available_data, _ = self._dev.WaitForAcquisitionUpdate(timeout_ms)
        except PicamError as e:
            if e.code == PicamEnums.Error.TimeOutOccurred:
                return False
            raise

    def latest_frame(self, copy=True):
        readouts = self._extract_available_data(self._latest_available_data, copy)
        return readouts[0][0][0]

    # /Generic Camera interface
    #

    #
    # New

    def _extract_available_data(self, available_data, copy=True):
        """Extract numpy arrays from available_data struct

        Parameters
        ----------
        available_data : <cdata 'struct PicamAvailableData'>
        copy : bool, optional
             Whether to copy the data out of the Picam struct.

        Returns
        -------
        A 3-D nested list of numpy arrays, indexed in order of (readout, frame, roi). Note that
        this is not 'rectangular' as the ROIs can have different sizes.
        """
        n_readouts = available_data.readout_count
        if n_readouts == 0:
            raise PicamError('There are no readouts in available_data')

        readout_stride = self.params.ReadoutStride.get_value()
        size = readout_stride * n_readouts

        all_data = _c_data_to_numpy(available_data.initial_readout, size, dtype=np.uint16)

        rois = self.params.Rois.get_value()
        roi_shapes = [(roi.width // roi.x_binning, roi.height // roi.y_binning) for roi in rois]

        def extract_roi_data(arr, frame_offset):
            roi_start = frame_offset
            for w,h in roi_shapes:
                roi_end = roi_start + w*h
                roi_data = np.reshape(arr[roi_start:roi_end], (h,w))
                yield roi_data.copy() if copy else roi_data
                roi_start = roi_end

        n_frames = self.params.FramesPerReadout.get_value()
        frame_stride = self.params.FrameStride.get_value()

        data = [
            [list(extract_roi_data(all_data, i*readout_stride + j*frame_stride))
             for j in range(n_frames)]
            for i in range(n_readouts)
        ]
        return data

    def set_roi(self, x=None, y=None, width=None, height=None, x_binning=None, y_binning=None):
        """Set one or more fields of the ROI

        If there are multiple ROIs, only applies to the first. Any args not given are left
        unmodified.
        """
        kwds = {k:v for k,v in vars().items() if k != 'self' and v is not None}
        rois = self.params.Rois.get_value()

        for name, value in kwds.items():
            setattr(rois[0], name, value)

        self.params.Rois.set_value(rois)

    def _get_rois(self):
        return self.params.Rois.get_value()

    def _get_rois_constraint(self):
        param = PicamEnums.Parameter.Rois
        category = PicamEnums.ConstraintCategory.Required
        rois_constraint = self._dev.GetParameterRoisConstraint(param, category)
        # NOTE: Do not keep references to sub-elements of this, as the memory will be cleaned
        # up once this object loses all direct Python references
        return ffi.gc(rois_constraint, ignore_error(NicePicamLib.DestroyRoisConstraints))

    # /New
    #

    #
    # Old

    #def set_frames(self, roi_list):
    #    """Sets the region(s) of interest for the camera.

    #    roi_list is a list containing region of interest elements, which can
    #    be either instances of ``PicamRois`` or dictionaries that can be used
    #    to instantiate ``PicamRois``"""
    #    for i in range(len(roi_list)):
    #        roi = roi_list[i]
    #        if not isinstance(roi, PicamRoi):
    #            roi = PicamRoi(**roi)
    #            roi_list[i] = roi
    #        if ((roi.width-roi.x) % roi.x_binning) != 0:
    #            text = "(width-x) must be an integer multiple of x_binning"
    #            raise(PicamError(text))
    #        if ((roi.height-roi.y) % roi.y_binning) != 0:
    #            text = "(height-y) must be an integer multiple of y_binning"
    #            raise(PicamError(text))
    #    rois = self._create_rois(roi_list)
    #    self._set_rois(rois)

    #def _create_rois(self, roi_list):
    #    """ Returns a C data PicamRois structure created from roi_list

    #    roi_list shoudl be a list containing instances of ``PicamRois``"""
    #    N_roi = len(roi_list)
    #    roi_array = self._ffi.new('struct PicamRoi[{}]'.format(N_roi))
    #    for i in range(N_roi):
    #        roi_i = roi_list[i]
    #        roi_array[i].x = roi_i.x
    #        roi_array[i].width = roi_i.width
    #        roi_array[i].x_binning = roi_i.x_binning
    #        roi_array[i].y = roi_i.y
    #        roi_array[i].height = roi_i.height
    #        roi_array[i].y_binning = roi_i.y_binning

    #    rois = self._ffi.new('struct PicamRois *')
    #    rois.roi_count = N_roi
    #    rois.roi_array = roi_array
    #    self.rois_keep_alive.append((rois, roi_array))
    #    return rois

    #def get_cameraID(self):
    #    """Returns the PicamID structure for the camera with name cam_name"""
    #    return self._NicePicam.GetCameraID()

    #def get_firmware_details(self):
    #    """Returns the camera firmware details"""
    #    firmware_array, count = NicePicamLib.GetFirmwareDetails(self.id)
    #    if count == 0:
    #        warn("No Firmware details available for camera {}".format(self.cam_name))
    #    firmware_details = {}
    #    for i in range(count):
    #        name = self._ffi.string(firmware_array[i].name)
    #        detail = self._ffi.string(firmware_array[i].detail)
    #        firmware_details[name] = detail
    #    NicePicamLib.DestroyFirmwareDetails(firmware_array)
    #    return firmware_details

    #def _turn_enum_into_integer(self, parameter, value=None):
    #    param_type = self.get_parameter_value_type(parameter)
    #    if value is not None:
    #        if param_type == self.enums.ValueType.Enumeration:
    #            value = value.value
    #    if param_type == self.enums.ValueType.Enumeration:
    #        param_type = self.enums.ValueType.Integer
    #    return param_type, value

    #def are_parameters_committed(self):
    #    """Whether or not the camera parameters are committed"""
    #    return bool(self._dev.AreParametersCommitted())

    def commit_parameters(self):
        """Commits camera parameters"""
        bad_params, n = self._dev.CommitParameters()

        if n > 0:
            bad_str = ','.join(PicamEnums.Parameter(bad_params[i]).name for i in range(n))
            raise PicamError("{} parameters were unsuccessfully committed: [{}]".format(n, bad_str))

    #def start_acquisition(self):
    #    """Begins an acquisition and returns immediately.

    #    The number of readouts is controlled by ``set_readout_count``.
    #    """
    #    self._NicePicam.StartAcquisition()

    #def stop_acquisition(self):
    #    """Stops a currently running acuisition"""
    #    self._NicePicam.StopAcquisition()

    #def is_aqcuisition_running(self):
    #    """Returns a boolean indicating whether an aqcuisition is running"""
    #    return bool(self._NicePicam.IsAcquisitionRunning())

    #@check_units(timeout = 'ms')
    #def wait_for_aqcuisition_update(self, timeout='-1ms'):
    #    """ Waits for a readout  """
    #    available, status = self._NicePicam.WaitForAcquisitionUpdate(timeout.to('ms').m)
    #    if status.errors != 0:
    #        raise PicamAcquisitionError(status.errors)
    #    return available, status

    #def get_readout_rate(self, default=False):
    #    """ Returns the readout rate (in units of Hz) of camera cam_name,
    #    given the current settings"""
    #    parameter = self.enums.Parameter.ReadoutRateCalculation
    #    return Q_(self._getset_param(parameter, default=default), 'Hz')

    #def get_readout_time(self, default=False):
    #    """ Returns the readout time (in ms) """
    #    param = self.enums.Parameter.ReadoutTimeCalculation
    #    return Q_(self._getset_param(param, default=default), 'ms')

    #@check_units(exposure = 'ms')
    #def set_exposure_time(self, exposure, canset=False):
    #    """sets the value of the exposure time """
    #    param = self.enums.Parameter.ExposureTime
    #    return self._getset_param(param, exposure.to('ms').m, canset)

    #def get_exposure_time(self, default=False):
    #    """Returns value of the exposure time """
    #    param = self.enums.Parameter.ExposureTime
    #    return Q_(self._getset_param(param, default=default), 'ms')

    #@check_enums(gain = PicamEnums.AdcAnalogGain)
    #def set_adc_gain(self, gain, canset=False):
    #    """Sets the ADC gain using an enum of type AdcAnalogGain."""
    #    param = self.enums.Parameter.AdcAnalogGain
    #    return self._getset_param(param, gain, canset)

    #def get_adc_gain(self, default=False):
    #    """Gets the ADC gain. """
    #    param = self.enums.Parameter.AdcAnalogGain
    #    value = self._getset_param(param, default=default)
    #    return self.enums.AdcAnalogGain(value)

    #@check_units(frequency='MHz')
    #def set_adc_speed(self, frequency, canset=False):
    #    """Sets the ADC Frequency

    #    For many cameras, the possible values are very constrained -
    #    typical ccd cameras accept only 2MHz and 0.1MHz work."""
    #    param = self.enums.Parameter.AdcSpeed
    #    return self._getset_param(param, frequency.to('MHz').m, canset)

    #def get_adc_speed(self, default=False):
    #    """Returns the ADC speed in MHz """
    #    param = self.enums.Parameter.AdcSpeed
    #    value = self._getset_param(param, default=default)
    #    return Q_(value, 'MHz')

    #def get_temperature_reading(self):
    #    """Returns the temperature of the sensor in degrees Centigrade"""
    #    param = self.enums.Parameter.SensorTemperatureReading
    #    return Q_(self._getset_param(param), 'celsius')

    #@check_units(temperature = 'celsius')
    #def set_temperature_setpoint(self, temperature, canset=False):
    #    """Set the temperature setpoint """
    #    param = self.enums.Parameter.SensorTemperatureSetPoint
    #    return self._getset_param(param, temperature.to('celsius').m, canset)

    #def get_temperature_setpoint(self, default=False):
    #    """Returns the temperature setpoint """
    #    param = self.enums.Parameter.SensorTemperatureSetPoint
    #    value = self._getset_param(param, default=default)
    #    return Q_(value, 'celsius')

    #def get_temperature_status(self):
    #    """Returns the temperature status """
    #    param = self.enums.Parameter.SensorTemperatureStatus
    #    return self.enums.SensorTemperatureStatus(self._getset_param(param))

    #def get_readout_count(self, default=False):
    #    """ Gets the number of readouts for an asynchronous aquire. """
    #    param = self.enums.Parameter.ReadoutCount
    #    return self._getset_param(param, default=default)

    #def set_readout_count(self, readout_count=None, canset=False):
    #    """ Sets the number of readouts for an asynchronous aquire.

    #    This does NOT affect the number of readouts for self.aqcuire
    #    """
    #    param = self.enums.Parameter.ReadoutCount
    #    return self._getset_param(param, readout_count, canset)

    #def get_time_stamp_mode(self, default=False):
    #    """ Get the mode for the timestamp portion of the frame metadata. """
    #    param = self.enums.Parameter.TimeStamps
    #    return self.enums.TimeStampsMask(self._getset_param(param, default=default))

    #@check_enums(gain = PicamEnums.AdcAnalogGain)
    #def set_time_stamp_mode(self, mode, canset=False):
    #    """ Sets the mode of the timestamp portion of the frame metadata using
    #    the enum ``TimeStampsMask`` """
    #    param = self.enums.Parameter.TimeStamps
    #    return self._getset_param(param, mode, canset)

    #@check_enums(mode = PicamEnums.ShutterTimingMode)
    #def set_shutter_mode(self, mode, canset=False):
    #    """ Controls the shutter operation mode using the enum ``ShutterTimingMode``."""
    #    param = self.enums.Parameter.ShutterTimingMode
    #    return self._getset_param(param, mode, canset)

    #def get_shutter_mode(self, default=False):
    #    """ Get the shutter operation mode."""
    #    param = self.enums.Parameter.ShutterTimingMode
    #    return self.enums.ShutterTimingMode(self._getset_param(param, default=default))

    #def open_shutter(self):
    #    """ Opens the shutter """
    #    self.set_shutter_mode(self.enums.ShutterTimingMode.AlwaysOpen)

    #def close_shutter(self):
    #    """ Closes the shutter """
    #    self.set_shutter_mode(self.enums.ShutterTimingMode.AlwaysClosed)

    #def normal_shutter(self):
    #    """ Puts the shutter into normal mode """
    #    self.set_shutter_mode(self.enums.ShutterTimingMode.Normal)

    #@check_enums(parameter = PicamEnums.Parameter)
    #def does_parameter_exist(self, parameter):
    #    """Returns a boolean indicating whether the parameter ``parameter`` exists"""
    #    return bool(self._NicePicam.DoesParameterExist(parameter.value))

    #@check_enums(parameter = PicamEnums.Parameter)
    #def is_parameter_relevant(self, parameter):
    #    """Returns a boolean indicating whether changing the parameter
    #    ``parameter`` will affect the behaviour of camera given the
    #    current settings"""
    #    return bool(self._NicePicam.IsParameterRelevant(parameter.value))

    #def get_parameter_list(self):
    #    """Returns an array of all the parameters of
    #    camera and the number of parameters"""
    #    parameter_list = []
    #    params, count = self._NicePicam.GetParameters()
    #    for i in range(count):
    #        parameter_list.append(self.enums.Parameter(params[i]))
    #    return parameter_list

    # /Old
    #


class _PicamSDK(object):
    _NicePicamLib = NicePicamLib
    _NicePicam = NicePicamLib.Camera
    _ffi = NicePicamLib._ffi
    _ffilib = NicePicamLib._ffilib
    enums = PicamEnums

    def __init__(self):
        self._open_count = 0
        self.cameras = {}

    def open(self):
        self._open_count += 1

        if not NicePicamLib.IsLibraryInitialized():
            NicePicamLib.InitializeLibrary()

    def close(self):
        self._open_count -= 1

        if self._open_count <= 0:
            for camera in self.cameras.values():
                camera.close()
            NicePicamLib.UninitializeLibrary()

    #def get_enumeration_string(self, enum_type, value):
    #    """Get the string associated with the enum 'value' of type 'enum_type'"""
    #    return NicePicamLib.GetEnumerationString(enum_type, value)

    #def is_demo_camera(self, cam_id=None):
    #    """
    #    Returns a boolean indicating whether the camera corresponding to
    #    cam_id is a demo camera
    #    """
    #    if cam_id is None:
    #        cam_id = self.cam
    #    return bool(NicePicamLib.IsDemoCamera(cam_id))

    #def get_version(self):
    #    """
    #    Returns a string containing version information for the Picam dll
    #    """
    #    major, minor, distribution, release = NicePicamLib.GetVersion()

    #    temp = (major, minor, distribution, release/100, release%100)
    #    version = 'Version {0[0]}.{0[1]}.{0[2]} released in 20{0[3]}-{0[4]}'
    #    return version.format(temp)

    def get_available_camera_IDs(self):
        """Returns an array of cameras that it is currently possible to
        connect to.

        Returns
        -------
        ID_array: array of PicamCameraID
            ids of the available cameras
        count: int
            the number of available cameras
        """
        id_array, count = NicePicamLib.GetAvailableCameraIDs()
        return PicamCameraID.from_array(id_array, count)

    #def get_unavailable_camera_IDs(self):
    #    """
    #    Returns an array of cameras that are either open or disconnected (it is
    #    not possible to connect to these cameras)

    #    Returns
    #    -------
    #    ID_array: array of PicamCameraID
    #        ids of the unavailable cameras
    #    count: int
    #        the number of unavailable cameras
    #    """
    #    ID_array, count = NicePicamLib.GetUnavailableCameraIDs()
    #    return ID_array, count

    #def destroy_camera_ids(self, cam_ids):
    #    """
    #    Destroys the memory associated with string the picam_id 'cam_id'
    #    """
    #    NicePicamLib.DestroyCameraIDs(cam_ids)

    def connect_demo_camera(self, model, serial_number):
        """Connects a demo camera of the specified model and serial number."""
        NicePicamLib.ConnectDemoCamera(model, serial_number)

    #def get_available_demo_camera_models(self):
    #    """
    #    Returns an array of all demo camera models that it is possible to
    #    create, and the length of that array.
    #    """
    #    models, count = NicePicamLib.GetAvailableDemoCameraModels()
    #    return models, count

    def disconnect_demo_camera(self, cam_id):
        """Disconnects the demo camera specified by cam_id"""
        NicePicamLib.DisconnectDemoCamera(cam_id._struct_ptr)

    #def destroy_models(self, models):
    #    """Releases memory associated with the array of cam_models 'models'"""
    #    NicePicamLib.DestroyModels(models)

    #def is_camera_connected(self, cam_id):
    #    """
    #    Returns a boolean indicating whether the camera matching cam_id is
    #    connected.

    #    Parameters
    #    -------
    #    cam_id: instance of PicamCameraID
    #    """
    #    return bool(NicePicamLib.IsCameraIDConnected(cam_id))

    #def is_camera_open_elsewhere(self, cam_id):
    #    """
    #    Returns a boolean indicating whether the camera matching cam_id
    #    is open in another program.

    #    Parameters
    #    -------
    #    cam_id: instance of PicamCameraID
    #    """
    #    return bool(NicePicamLib.IsCameraIDOpenElsewhere(cam_id))

    #def open_first_camera(self, cam_name):
    #    """
    #    Opens the first available camera, and assigns it the name 'cam_name'
    #    """
    #    ID_array, count = self.get_available_camera_IDs()
    #    if count == 0:
    #        raise PicamError('No cameras available - could not open first camera')
    #    if count == 1:
    #        id = ID_array
    #    else:
    #        id = ID_array[0]
    #    self.open_camera(id, cam_name)

    #def add_camera(self, cam_name, nice_cam):
    #    """Adds a camera with the name cam_name to the dictionary of cameras, self.cameras"""
    #    if cam_name in self.cameras:
    #        raise PicamError('Camera name {} already in use'.format(cam_name))
    #    self.cameras[cam_name] = PicamCamera(nice_cam, self)

    #def open_camera(self, cam_id : PicamCameraID, cam_name : str):
    #    """Opens the camera associated with cam_id, and assigns it the name 'cam_name'"""
    #    #handle = NicePicamLib.OpenCamera(cam_id)
    #    nice_cam = NicePicamLib.Camera(cam_id)
    #    self.add_camera(cam_name, nice_cam)

    #def open_cameras(self, cam_dict):
    #    IDarray, n = self.get_available_camera_IDs()
    #    for cam_name in cam_dict.keys():
    #        for i in range(n):
    #            if IDarray[i].model == cam_dict[cam_name]:
    #                self.open_camera(IDarray[i], i)
    #                break
    #            if i == n-1:
    #                raise(PicamError("Camera {} does not exist".format(cam_name)))

    #def destroy_rois(self, rois):
    #    """Releases the memory associated with PicamRois structure 'rois'.

    #    NOTE: this only works for instances of rois created from
    #    'getset_rois', and not for user-created rois from 'create_rois'
    #    """
    #    NicePicamLib.DestroyRois(rois)


sdk = _PicamSDK()  # singleton
sdk.open()
register_cleanup(sdk.close)
