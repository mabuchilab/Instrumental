# -*- coding: utf-8 -*-
"""
Copyright 2015 Christopher Rogers

Class to control Princeton Instruments Cameras using the PICAM SDK

Installation
----------------
The PICAM SDK must be installed.  It is available from the Princeton
Instruments ftp site.
The .dlls Picam.dll Picc.dll, Pida.dll and Pidi.dll must be copied to a
directory on the system path.
Note that the .dlls found first on the system path must match the version
of the headers installed with the Picam SDK.
"""

from warnings import warn
from numpy import frombuffer, sum, uint16, hstack, vstack
from enum import Enum
from nicelib import NiceLib, NiceObjectDef, load_lib
from ...errors import Error, InstrumentNotFoundError
from ..util import check_units, check_enums
from ... import Q_


class PicamError(Error):
    pass


lib = load_lib('picam', __package__)
BYTES_PER_PIXEL = 2

class NicePicamLib(NiceLib):
    """Wrapper for Picam.dll"""
    _info = lib
    _buflen = 256
    _prefix = 'Picam_'
    _ret_wrap = 'error'
    
    def _ret_error(error):
        if error != 0:
            if bool(NicePicamLib.IsLibraryInitialized()):
                NicePicamLib.GetEnumerationString(lib.PicamEnumeratedType_Error, error)
            else:
               NicePicamLib._ret_enum_string_error(error)

    def _ret_enum_string_error(error):
        if error != 0:
            if error == lib.PicamError_LibraryNotInitialized:
                raise PicamError('Library not initialized')
            if error == lib.PicamError_InvalidEnumeratedType:
                raise PicamError('Invalid enumerated Type')
            if error == lib.PicamError_EnumerationValueNotDefined:
                raise PicamError('Enumeration value not defined.')
            else:
                raise PicamError('Error when getting enumeration string.  Error code {}'.format(error))

    GetVersion = ('out', 'out', 'out', 'out')
    IsLibraryInitialized = ('out', {'ret':'ignore'})
    InitializeLibrary = ()
    UninitializeLibrary = ()
    DestroyString = ('in')
    GetEnumerationString = ('in', 'in', 'bufout', {'ret':'enum_string_error'})
    DestroyCameraIDs = ('in')
    GetAvailableCameraIDs = ('out', 'out')
    GetUnavailableCameraIDs = ('out', 'out')
    IsCameraIDConnected = ('in', 'out')
    IsCameraIDOpenElsewhere = ('in', 'out')
    DestroyHandles = ('in')
    OpenFirstCamera = ('out')
    OpenCamera = ('in', 'out')
    # DestroyFirmwareDetails = (firmware_array)
    DestroyFirmwareDetails = ('in')
    # DestroyModels = (model_array)
    DestroyModels = ('in')
    GetAvailableDemoCameraModels = ('out', 'out')
    ConnectDemoCamera = ('in', 'in', 'out')
    DisconnectDemoCamera = ('in')
    GetOpenCameras = ('out', 'out')
    IsDemoCamera = ('in', 'out')
    # GetFirmwareDetails = (id, firmware_array, firmware_count)
    GetFirmwareDetails = ('in', 'out', 'out')
    # DestroyRois = (rois)
    DestroyRois = ('in')
    # DestroyModulations = (modulations)
    DestroyModulations = ('in')
    # DestroyPulses = (pulses)
    DestroyPulses = ('in')
    # DestroyParameters = (parameter_array)
    DestroyParameters = ('in')
    # DestroyCollectionConstraints = (constraint_array)
    DestroyCollectionConstraints = ('in')
    # DestroyRangeConstraints = (constraint_array)
    DestroyRangeConstraints = ('in')
    # DestroyRoisConstraints = (constraint_array)
    DestroyRoisConstraints = ('in')
    # DestroyModulationsConstraints = (constraint_array)
    DestroyModulationsConstraints = ('in')
    # DestroyPulseConstraints = (constraint_array)
    DestroyPulseConstraints = ('in')
    
    NicePicam = NiceObjectDef({
    'CloseCamera': ('in'),
    'IsCameraConnected': ('in', 'out'),
    'GetCameraID': ('in', 'out'),
    # GetParameterIntegerValue': (camera, parameter, value),
    'GetParameterIntegerValue': ('in', 'in', 'out'),
    # SetParameterIntegerValue': (camera, parameter, value),
    'SetParameterIntegerValue': ('in', 'in', 'in'),
    # CanSetParameterIntegerValue': (camera, parameter, value, settable),
    'CanSetParameterIntegerValue': ('in', 'in', 'in', 'out'),
    # GetParameterLargeIntegerValue': (camera, parameter, value),
    'GetParameterLargeIntegerValue': ('in', 'in', 'out'),
    # SetParameterLargeIntegerValue': (camera, parameter, value),
    'SetParameterLargeIntegerValue': ('in', 'in', 'in'),
    # CanSetParameterLargeIntegerValue': (camera, parameter, value, settable),
    'CanSetParameterLargeIntegerValue': ('in', 'in', 'in', 'out'),
    # GetParameterFloatingPointValue': (camera, parameter, value),
    'GetParameterFloatingPointValue': ('in', 'in', 'out'),
    # SetParameterFloatingPointValue': (camera, parameter, value),
    'SetParameterFloatingPointValue': ('in', 'in', 'in'),
    # CanSetParameterFloatingPointValue': (camera, parameter, value, settable),
    'CanSetParameterFloatingPointValue': ('in', 'in', 'in', 'out'),
    # GetParameterRoisValue': (camera, parameter, value),
    'GetParameterRoisValue': ('in', 'in', 'out'),
    # SetParameterRoisValue': (camera, parameter, value),
    'SetParameterRoisValue': ('in', 'in', 'in'),
    # CanSetParameterRoisValue': (camera, parameter, value, settable),
    'CanSetParameterRoisValue': ('in', 'in', 'in', 'out'),
    # GetParameterPulseValue': (camera, parameter, value),
    'GetParameterPulseValue': ('in', 'in', 'out'),
    # SetParameterPulseValue': (camera, parameter, value),
    'SetParameterPulseValue': ('in', 'in', 'in'),
    # CanSetParameterPulseValue': (camera, parameter, value, settable),
    'CanSetParameterPulseValue': ('in', 'in', 'in', 'out'),
    # GetParameterModulationsValue': (camera, parameter, value),
    'GetParameterModulationsValue': ('in', 'in', 'out'),
    # SetParameterModulationsValue': (camera, parameter, value),
    'SetParameterModulationsValue': ('in', 'in', 'in'),
    # CanSetParameterModulationsValue': (camera, parameter, value, settable),
    'CanSetParameterModulationsValue': ('in', 'in', 'in', 'out'),
    # GetParameterIntegerDefaultValue': (camera, parameter, value),
    'GetParameterIntegerDefaultValue': ('in', 'in', 'out'),
    # GetParameterLargeIntegerDefaultValue': (camera, parameter, value),
    'GetParameterLargeIntegerDefaultValue': ('in', 'in', 'out'),
    # GetParameterFloatingPointDefaultValue': (camera, parameter, value),
    'GetParameterFloatingPointDefaultValue': ('in', 'in', 'out'),
    # GetParameterRoisDefaultValue': (camera, parameter, value),
    'GetParameterRoisDefaultValue': ('in', 'in', 'out'),
    # GetParameterPulseDefaultValue': (camera, parameter, value),
    'GetParameterPulseDefaultValue': ('in', 'in', 'out'),
    # GetParameterModulationsDefaultValue': (camera, parameter, value),
    'GetParameterModulationsDefaultValue': ('in', 'in', 'out'),
    # CanSetParameterOnline': (camera, parameter, onlineable),
    'CanSetParameterOnline': ('in', 'in', 'out'),
    # SetParameterIntegerValueOnline': (camera, parameter, value),
    'SetParameterIntegerValueOnline': ('in', 'in', 'in'),
    # SetParameterFloatingPointValueOnline': (camera, parameter, value),
    
    'SetParameterFloatingPointValueOnline': ('in', 'in', 'in'),
    # SetParameterPulseValueOnline': (camera, parameter, value),
    'SetParameterPulseValueOnline': ('in', 'in', 'in'),
    # CanReadParameter': (camera, parameter, readable),
    'CanReadParameter': ('in', 'in', 'out'),
    # ReadParameterIntegerValue': (camera, parameter, value),
    'ReadParameterIntegerValue': ('in', 'in', 'out'),
    # ReadParameterFloatingPointValue': (camera, parameter, value),
    'ReadParameterFloatingPointValue': ('in', 'in', 'out'),
    # GetParameters': (camera, parameter_array, parameter_count),
    'GetParameters': ('in', 'out', 'out'),
    # DoesParameterExist': (camera, parameter, exists),
    'DoesParameterExist': ('in', 'in', 'out'),
    # IsParameterRelevant': (camera, parameter, relevant),
    'IsParameterRelevant': ('in', 'in', 'out'),
    # GetParameterValueType': (camera, parameter, type),
    'GetParameterValueType': ('in', 'in', 'out'),
    # GetParameterEnumeratedType': (camera, parameter, type),
    'GetParameterEnumeratedType': ('in', 'in', 'out'),
    # GetParameterValueAccess': (camera, parameter, access),
    'GetParameterValueAccess': ('in', 'in', 'out'),
    # GetParameterConstraintType': (camera, parameter, type),
    'GetParameterConstraintType': ('in', 'in', 'out'),
    # GetParameterCollectionConstraint': (camera, parameter, category, constraint),
    'GetParameterCollectionConstraint': ('in', 'in', 'in', 'out'),
    # GetParameterRangeConstraint': (camera, parameter, category, constraint),
    'GetParameterRangeConstraint': ('in', 'in', 'in', 'out'),
    # GetParameterRoisConstraint': (camera, parameter, category, constraint),
    'GetParameterRoisConstraint': ('in', 'in', 'in', 'out'),
    # GetParameterPulseConstraint': (camera, parameter, category, constraint),
    'GetParameterPulseConstraint': ('in', 'in', 'in', 'out'),
    # GetParameterModulationsConstraint': (camera, parameter, category, constraint),
    'GetParameterModulationsConstraint': ('in', 'in', 'in', 'out'),
    # AreParametersCommitted': (camera, committed),
    'AreParametersCommitted': ('in', 'out'),
    # CommitParameters': (camera, failed_parameter_array, failed_parameter_count),
    'CommitParameters': ('in', 'out', 'out'),
    # Acquire': (camera, readout_count, readout_time_out, available, errors),
    'Acquire': ('in', 'in', 'in', 'out', 'out'),
    # StartAcquisition': (camera),
    'StartAcquisition': ('in'),
    # StopAcquisition': (camera),
    'StopAcquisition': ('in'),
    # IsAcquisitionRunning': (camera, running),
    'IsAcquisitionRunning': ('in', 'out'),
    # WaitForAcquisitionUpdate': (camera, readout_time_out, available, status),
    'WaitForAcquisitionUpdate': ('in', 'in', 'out', 'out')
    })


class EnumTypes():
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
                    if not enum_type_dict.has_key(enum_type):
                        enum_type_dict[enum_type] = {}
                    enum_type_dict[enum_type][enum_name] = value
        for enum_type, enum_dict in enum_type_dict.items():
            if isinstance(enum_dict, dict):
                enum_type_dict[enum_type] = Enum(enum_type, enum_dict)
        return enum_type_dict

PicamEnums = EnumTypes()

class PicamRoi():
    """ Class defining a region of interest.  
    All values are in pixels.  """
    def __init__(self, x, width, y, height, x_binning=1, y_binning=1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.x_binning = x_binning
        self.y_binning = y_binning

class PicamAcquisitionError(PicamError):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        if self.value == NicePicamLib._ffilib.PicamAcquisitionErrorsMask_None:
            return "No error occured"
        elif self.value == NicePicamLib._ffilib.PicamAcquisitionErrorsMask_DataLost:
            return "DataLost"
        elif self.value == NicePicamLib._ffilib.PicamAcquisitionErrorsMask_ConnectionLost:
            return "ConnectionLost"
        else:
            return "An unkown error with code {}".format(self.value)

class PicamCamera():
    """ A Picam Camera """
    def __init__(self, name, handle, NicePicam, ffi, NicePicamLib, picam):
        self.picam = picam
        self.name = name
        self.handle = handle
        self._NicePicam = NicePicam
        self._ffi = ffi
        self._ffilib = NicePicamLib._ffilib
        self._NicePicamLib = NicePicamLib
        self.rois = None
        self.enums = PicamEnums
        self.id = self._ffi.addressof(self._NicePicam.GetCameraID())
        self._update_rois()
        self._rois_keep_alive = []

    def _update_rois(self):
        self.rois_keep_alive = []
        if self.rois is not None:
            self.picam.destroy_rois(self.rois)
        self.rois = self._get_rois()
        self.frame_shapes = self.get_frame_shapes()
        self.readout_stride = self._get_readout_stride()
        self.n_pixels_per_readout = self.readout_stride/BYTES_PER_PIXEL

    def _set_rois(self, rois, canset=False):
        """ Set the region of interest structure. """
        param = self.enums.Parameter.Rois
        retval = self._getset_param(param, rois, canset)
        if not canset:
            self._update_rois()
        return retval

    def _get_rois(self, default=False):
        param = self.enums.Parameter.Rois
        return self._getset_param(param, default=default)

    def set_frames(self, roi_list):
        """Sets the region(s) of interest for the camera.

        roi_list is a list containing region of interest elements, which can
        be either instances of ``PicamRois`` or dictionaries that can be used
        to instantiate ``PicamRois``"""
        for i in range(len(roi_list)):
            roi = roi_list[i]
            if not isinstance(roi, PicamRoi):
                roi = PicamRoi(**roi)
                roi_list[i] = roi
            if ((roi.width-roi.x) % roi.x_binning) != 0:
                text = "(width-x) must be an integer multiple of x_binning"
                raise(PicamError(text))
            if ((roi.height-roi.y) % roi.y_binning) != 0:
                text = "(height-y) must be an integer multiple of y_binning"
                raise(PicamError(text))
        rois = self._create_rois(roi_list)
        self._set_rois(rois)

    def _create_rois(self, roi_list):
        """ Returns a C data PicamRois structure created from roi_list
        
        roi_list shoudl be a list containing instances of ``PicamRois``"""
        N_roi = len(roi_list)
        roi_array = self._ffi.new('struct PicamRoi[{}]'.format(N_roi))
        for i in range(N_roi):
            roi_i = roi_list[i]
            roi_array[i].x = roi_i.x
            roi_array[i].width = roi_i.width
            roi_array[i].x_binning = roi_i.x_binning
            roi_array[i].y = roi_i.y
            roi_array[i].height = roi_i.height
            roi_array[i].y_binning = roi_i.y_binning

        rois = self._ffi.new('struct PicamRois *')
        rois.roi_count = N_roi
        rois.roi_array = roi_array
        self.rois_keep_alive.append((rois, roi_array))
        return rois

    def close(self):
        """ Close the connection to the camera"""
        self._NicePicam.CloseCamera()

    def get_cameraID(self):
        """Returns the PicamID structure for the camera with name cam_name"""
        return self._NicePicam.GetCameraID()

    def get_firmware_details(self):
        """Returns the camera firmware details"""
        firmware_array, count = self._NicePicamLib.GetFirmwareDetails(self.id)
        if count == 0:
            warn("No Firmware details available for camera {}".format(self.cam_name))
        firmware_details = {}
        for i in range(count):
            name = self._ffi.string(firmware_array[i].name)
            detail = self._ffi.string(firmware_array[i].detail)
            firmware_details[name] = detail
        self._destroy_firmware_details(firmware_array)
        return firmware_details

    def _destroy_firmware_details(self, firmware_array):
        """Releases the memory associated with the firmware details
        ``firmware_array`` """
        self._NicePicamLib.DestroyFirmwareDetails(firmware_array)

    def _get_readout_stride(self, default=False):
        """Returns the length of a readout in bytes.  """
        param = self.enums.Parameter.ReadoutStride
        return self._getset_param(param, default=default)

    def get_param(self, parameter, default=False):
        """ Returns the value of the specified parameter.
        
        ``parameter`` should be an integer of corresponding to a PicamParameter
        enumerator.
        If ``default`` is ``True``, then the default value of the parameter is
        returned."""
        return self._getset_param(parameter, default=default)

    def set_param(self, parameter, value=None, canset=False):
        """ Sets the value of the specified parameter to ``value``.
        
        ``parameter`` should be an integer of corresponding to a PicamParameter
        enumerator.
        If ``canset`` is ``True``, then a boolean indicating whether it is possible
        to set the parameter to ``value`` is returned.  Note that this does not
        actually set the parameter."""
        return self._getset_param(parameter, value, canset)

    def _getset_param(self, parameter, value=None, canset=False,
                     default=False, commit=True):
        """Gets or sets the value of parameter 'parameter' for camera
        cam_name

        If value==None and canset==False, the value of parameter is returned.
        If value is not None and canset==False, the value of parameter is set
        to value.
        If value is not None and canset==True, a boolean indicating whether
        parameter can be set to value is returned.
        If default==False, then the default value of the parameter is returned
        """
        parameter = parameter.value
        if default:
            return self._getParameterDefaultValue(parameter)
        if value is not None:
            settable = self._canSetParameterValue(parameter, value)
        if canset is True:
            return settable
        if value is not None:
            if settable:
                self._setParameterValue(parameter, value)
                self.commit_parameters()
                return
            else:
                raise(PicamError("Value is not settable"))
                return
        value = self._getParameterValue(parameter)
        return value

    def get_parameter_value_type(self, parameter_type):
        """Returns an enumerator of ``ValueType`` indicating the data
        type associated with ``parameter_type``"""
        value_type = self._NicePicam.GetParameterValueType(parameter_type)
        return self.enums.ValueType(value_type)

    def _turn_enum_into_integer(self, parameter, value=None):
        param_type = self.get_parameter_value_type(parameter)
        if value is not None:
            if param_type == self.enums.ValueType.Enumeration:
                value = value.value
        if param_type == self.enums.ValueType.Enumeration:
            param_type = self.enums.ValueType.Integer
        return param_type, value

    def _getParameterValue(self, parameter):
        """Returns the value of parameter ``parameter`` for camera cam_name"""
        data_type, _ = self._turn_enum_into_integer(parameter)
        if data_type == self.enums.ValueType.Rois:
            value = self._NicePicam.GetParameterRoisValue(parameter)
            return value
        if data_type == self.enums.ValueType.FloatingPoint:
            return self._NicePicam.GetParameterFloatingPointValue(parameter)
        elif data_type == self.enums.ValueType.Integer:
            return self._NicePicam.GetParameterIntegerValue(parameter)
        elif data_type == self.enums.ValueType.LargeInteger:
            return self._NicePicam.GetParameterLargeIntegerValue(parameter)

    def _setParameterValue(self, parameter, value):
        """Sets the value of the parameter ``parameter`` to value 'value'"""
        data_type, value = self._turn_enum_into_integer(parameter, value)
        if data_type == self.enums.ValueType.Rois:
            self._NicePicam.SetParameterRoisValue(parameter, value)
        elif data_type == self.enums.ValueType.FloatingPoint:
            self._NicePicam.SetParameterFloatingPointValue(parameter, value)
        elif data_type == self.enums.ValueType.Integer:
            self._NicePicam.SetParameterIntegerValue(parameter, value)
        elif data_type == self.enums.ValueType.LargeInteger:
            self._NicePicam.SetParameterLargeIntegerValue(parameter, value)

    def _canSetParameterValue(self, parameter, value):
        """Returns a boolean indicating whether the parameter ``parameter`` can
        be set to value 'value'"""
        data_type, value = self._turn_enum_into_integer(parameter, value)
        if data_type == self.enums.ValueType.Rois:
            can_set = self._NicePicam.CanSetParameterRoisValue(parameter, value)
        elif data_type == self.enums.ValueType.FloatingPoint:
            can_set = self._NicePicam.CanSetParameterFloatingPointValue(parameter, value)
        elif data_type == self.enums.ValueType.Integer:
            can_set = self._NicePicam.CanSetParameterIntegerValue(parameter, value)
        elif data_type == self.enums.ValueType.LargeInteger:
            can_set = self._NicePicam.CanSetParameterLargeIntegerValue(parameter, value)
        return bool(can_set)

    def _getParameterDefaultValue(self, parameter):
        """Returns the default value of parameter ``parameter`` for camera
        cam_name"""
        data_type, _ = self._turn_enum_into_integer(parameter)
        if data_type == self.enums.ValueType.Rois:
            value = self._NicePicam.GetParameterRoisDefaultValue(parameter)
            return value
        if data_type == self.enums.ValueType.FloatingPoint:
            return self._NicePicam.GetParameterFloatingPointDefaultValue(parameter)
        elif data_type == self.enums.ValueType.Integer:
            return self._NicePicam.GetParameterIntegerDefaultValue(parameter)
        elif data_type == self.enums.ValueType.LargeInteger:
            return self._NicePicam.GetParameterLargeIntegerDefaultValue(parameter)

    def are_parameters_committed(self):
        """Returns a boolean indicating whether or not the camera parameters
        are committed"""
        return bool(self._NicePicam.AreParametersCommitted())

    def commit_parameters(self):
        """Commits camera parameters."""
        uncommitted, N = self._NicePicam.CommitParameters()
        if N != 0:
            raise PicamError("{} parameters were unsuccessfully committed.")

    def _c_address_to_numpy(self, address, size, data_type=float):
        """ Creates a numpy array from a c array at ``address`` with bytesize
        ``size`` """
        ffi = self._NicePicamLib._ffi
        # This copies the buffer
        buf = buffer(ffi.buffer(address, size)[:])
        return frombuffer(buf, data_type)

    def get_frame_shapes(self, rois=None):
        """Returns the region of interest frame shapes as a list of tuples
        
        The tuples correspond to the number of x and y pixels in each region of interest

        If rois is None, then the current region of interest array is used
        """
        if rois is None:
            rois = self.rois
        shapes = []
        for i in range(rois.roi_count):
            roi = rois.roi_array[i]
            x = roi.width/roi.x_binning
            y = roi.height/roi.y_binning
            shapes = shapes + [(x, y)]
        return shapes

    def start_acquisition(self):
        """ This function begins an acquisition and returns immediately.

        The number of readouts is controlled by ``set_readout_count``.
        """
        self._NicePicam.StartAcquisition()

    def stop_acquisition(self):
        """Stops a currently running acuisition"""
        self._NicePicam.StopAcquisition()

    def is_aqcuisition_running(self):
        """Returns a boolean indicating whether an aqcuisition is running"""
        return bool(self._NicePicam.IsAcquisitionRunning())

    @check_units(timeout = 'ms')
    def wait_for_aqcuisition_update(self, timeout='-1ms'):
        """ Waits for a readout  """
        available, status = self._NicePicam.WaitForAcquisitionUpdate(timeout.to('ms').m)
        if status.errors != 0:
            raise PicamAcquisitionError(status.errors)
        return available, status

    def get_data_from_available(self, available_data, average=False):
        """Returns an array of data corresponding to the data buffer given
        by the PicamAvailableData structure
        """
        count = available_data.readout_count
        if count == 0:
            raise PicamError('There are no readouts in available_data')
        readout_stride = self._get_readout_stride()
        size = readout_stride * available_data.readout_count
        data = self._c_address_to_numpy(available_data.initial_readout,
                                        size, uint16)
        data_list = []
        index_start = 0
        # loop over each roi
        for shape in self.frame_shapes:
            n_roi_pixels = shape[0]*shape[1]
            index_end = n_roi_pixels + index_start
            roi_data = data[index_start:index_end]
            # loop over each readout
            for i in range(1, count):
                index_1 = index_start + i * self.n_pixels_per_readout
                index_2 = index_end + i * self.n_pixels_per_readout
                temp = data[index_1:index_2]
                roi_data = vstack([roi_data, temp])
            roi_data = roi_data.reshape((count,) + shape[::-1])

            if count==1:
                roi_data = roi_data[0,:,:]

            if average:
                roi_data = sum(roi_data, 2)/float(count)

            data_list.append(roi_data)
            index_start = index_end

        if len(self.frame_shapes) == 1:
            return data_list[0]
        else:
            return data_list

    @check_units(timeout = 'ms')
    def get_data(self, count=1, timeout='-1ms', average=False):
        """Returns a numpy array of the pixel data for the specified camera.

        Note that this only works if there is a single ROI"""
        available_data, error = self._NicePicam.Acquire(count,
                                                        timeout.to('ms').m)
        if error != 0:
            raise PicamAcquisitionError()
        return self.get_data_from_available(available_data, average)

    def get_readout_rate(self, default=False):
        """ Returns the readout rate (in units of Hz) of camera cam_name,
        given the current settings"""
        parameter = self.enums.Parameter.ReadoutRateCalculation
        return Q_(self._getset_param(parameter, default=default), 'Hz')

    def get_readout_time(self, default=False):
        """ Returns the readout time (in ms) """
        param = self.enums.Parameter.ReadoutTimeCalculation
        return Q_(self._getset_param(param, default=default), 'ms')

    @check_units(exposure = 'ms')
    def set_exposure_time(self, exposure, canset=False):
        """sets the value of the exposure time """
        param = self.enums.Parameter.ExposureTime
        return self._getset_param(param, exposure.to('ms').m, canset)

    def get_exposure_time(self, default=False):
        """Returns value of the exposure time """
        param = self.enums.Parameter.ExposureTime
        return Q_(self._getset_param(param, default=default), 'ms')

    @check_enums(gain = PicamEnums.AdcAnalogGain)
    def set_adc_gain(self, gain, canset=False):
        """Sets the ADC gain using an enum of type AdcAnalogGain."""
        param = self.enums.Parameter.AdcAnalogGain
        return self._getset_param(param, gain, canset)

    def get_adc_gain(self, default=False):
        """Gets the ADC gain. """
        param = self.enums.Parameter.AdcAnalogGain
        value = self._getset_param(param, default=default)
        return self.enums.AdcAnalogGain(value)

    @check_units(frequency='MHz')
    def set_adc_speed(self, frequency, canset=False):
        """Sets the ADC Frequency

        For many cameras, the possible values are very constrained - 
        typical ccd cameras accept only 2MHz and 0.1MHz work."""
        param = self.enums.Parameter.AdcSpeed
        return self._getset_param(param, frequency.to('MHz').m, canset)

    def get_adc_speed(self, default=False):
        """Returns the ADC speed in MHz """
        param = self.enums.Parameter.AdcSpeed
        value = self._getset_param(param, default=default)
        return Q_(value, 'MHz')

    def get_temperature_reading(self):
        """Returns the temperature of the sensor in degrees Centigrade"""
        param = self.enums.Parameter.SensorTemperatureReading
        return Q_(self._getset_param(param), 'celsius')

    @check_units(temperature = 'celsius')
    def set_temperature_setpoint(self, temperature, canset=False):
        """Set the temperature setpoint """
        param = self.enums.Parameter.SensorTemperatureSetPoint
        return self._getset_param(param, temperature.to('celsius').m, canset)

    def get_temperature_setpoint(self, default=False):
        """Returns the temperature setpoint """
        param = self.enums.Parameter.SensorTemperatureSetPoint
        value = self._getset_param(param, default=default)
        return Q_(value, 'celsius')

    def get_temperature_status(self):
        """Returns the temperature status """
        param = self.enums.Parameter.SensorTemperatureStatus
        return self.enums.SensorTemperatureStatus(self._getset_param(param))

    def get_readout_count(self, default=False):
        """ Gets the number of readouts for an asynchronous aquire. """
        param = self.enums.Parameter.ReadoutCount
        return self._getset_param(param, default=default)

    def set_readout_count(self, readout_count=None, canset=False ):
        """ Sets the number of readouts for an asynchronous aquire.

        This does NOT affect the number of readouts for self.aqcuire
        """
        param = self.enums.Parameter.ReadoutCount
        return self._getset_param(param, readout_count, canset)

    def get_time_stamp_mode(self, default=False):
        """ Get the mode for the timestamp portion of the frame metadata. """
        param = self.enums.Parameter.TimeStamps
        return self.enums.TimeStampsMask(self._getset_param(param,
                                                           default=default))

    @check_enums(gain = PicamEnums.AdcAnalogGain)
    def set_time_stamp_mode(self, mode, canset=False):
        """ Sets the mode of the timestamp portion of the frame metadata using
        the enum ``TimeStampsMask`` """
        param = self.enums.Parameter.TimeStamps
        return self._getset_param(param, mode, canset)

    @check_enums(mode = PicamEnums.ShutterTimingMode)
    def set_shutter_mode(self, mode, canset=False):
        """ Controls the shutter operation mode using the enum ``ShutterTimingMode``."""
        param = self.enums.Parameter.ShutterTimingMode
        return self._getset_param(param, mode, canset)

    def get_shutter_mode(self, default=False):
        """ Get the shutter operation mode."""
        param = self.enums.Parameter.ShutterTimingMode
        return self.enums.ShutterTimingMode(self._getset_param(param,
                                                              default=default))

    def open_shutter(self):
        """ Opens the shutter """
        self.set_shutter_mode(self.enums.ShutterTimingMode.AlwaysOpen)

    def close_shutter(self):
        """ Closes the shutter """
        self.set_shutter_mode(self.enums.ShutterTimingMode.AlwaysClosed)

    def normal_shutter(self):
        """ Puts the shutter into normal mode """
        self.set_shutter_mode(self.enums.ShutterTimingMode.Normal)

    @check_enums(parameter = PicamEnums.Parameter)
    def does_parameter_exist(self, parameter):
        """Returns a boolean indicating whether the parameter ``parameter``
        exists"""
        return bool(self._NicePicam.DoesParameterExist(parameter.value))

    @check_enums(parameter = PicamEnums.Parameter)
    def is_parameter_relevant(self, parameter):
        """Returns a boolean indicating whether changing the parameter
        ``parameter`` will affect the behaviour of camera given the
        current settings"""
        return bool(self._NicePicam.IsParameterRelevant(parameter.value))

    def get_parameter_list(self):
        """Returns an array of all the parameters of
        camera and the number of parameters"""
        parameter_list = []
        params, count = self._NicePicam.GetParameters()
        for i in range(count):
            parameter_list.append(self.enums.Parameter(params[i]))
        return parameter_list


class Picam():
    def __init__(self, cameras=None, usedemo=False, default_cam=None):
        NicePicamLib.InitializeLibrary()
        self.cameras = {}
        self._ffi = NicePicamLib._ffi
        self._NicePicamLib = NicePicamLib
        self.enums = PicamEnums

        if usedemo:
            cam_id = self._ffi.addressof(NicePicamLib.ConnectDemoCamera(10, '1234'))
            cameras = {'demo_camera': cam_id}

        if cameras is None:
            self.cams = {}
            default_cam = 'first_camera'
            self.open_first_camera(default_cam)   
        else:
            for name, cam_id in cameras.iteritems():
                self.open_camera(cam_id, name)

        if default_cam is None:
            self.default_cam = cameras.keys()[0]
        else:
            if default_cam in self.cameras:
                self.default_cam = default_cam
            else:
                raise PicamError("Default camera {} does not exist".format(default_cam))

    def close(self):
        for camera in self.cameras.items:
            camera.close()
        self._NicePicamLib.UninitializeLibrary()

    def get_enumeration_string(self, enum_type, value):
        """ Returns the string of the associated with the enum 'value' of type
        'enumeration type'"""
        return self._NicePicamLib.GetEnumerationString(enum_type, value)

    def is_demo_camera(self, cam_id=None):
        """
        Returns a boolean indicating whether the camera corresponding to
        cam_id is a demo camera
        """
        if cam_id is None:
            cam_id = self.cam
        return bool(self._NicePicamLib.IsDemoCamera(cam_id))

    def get_version(self):
        """
        Returns a string containing version information for the Picam dll
        """
        major, minor, distribution, release = self._NicePicamLib.GetVersion()
        
        temp = (major, minor, distribution, release/100, release%100)
        version = 'Version {0[0]}.{0[1]}.{0[2]} released in 20{0[3]}-{0[4]}'
        return version.format(temp)

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
        ID_array, count = self._NicePicamLib.GetAvailableCameraIDs()
        return ID_array, count

    def get_unavailable_camera_IDs(self):
        """
        Returns an array of cameras that are either open or disconnected (it is
        not possible to connect to these cameras)

        Returns
        -------
        ID_array: array of PicamCameraID
            ids of the unavailable cameras
        count: int
            the number of unavailable cameras
        """
        ID_array, count = self._NicePicamLib.GetUnavailableCameraIDs()
        return ID_array, count

    def destroy_camera_ids(self, cam_ids):
        """
        Destroys the memory associated with string the picam_id 'cam_id'
        """
        self._NicePicamLib.DestroyCameraIDs(cam_ids)

    def connect_demo_camera(self, model, serial_number):
        """Connects a demo camera of the specified model and serial number."""
        self._NicePicamLib.ConnectDemoCamera(model, serial_number)

    def get_available_demo_camera_models(self):
        """
        Returns an array of all demo camera models that it is possible to
        create, and the length of that array.
        """
        models, count = self._NicePicamLib.GetAvailableDemoCameraModels()
        return models, count

    def disconnect_demo_camera(self, cam_id):
        """
        Disconnects the demo camera specified by cam_id
        """
        self._NicePicamLib.DisconnectDemoCamera(cam_id)

    def destroy_models(self, models):
        """Releases memory associated with the array of cam_models 'models'"""
        self._NicePicamLib.DestroyModels(models)

    def is_camera_connected(self, cam_id):
        """
        Returns a boolean indicating whether the camera matching cam_id is
        connected.

        Parameters
        -------
        cam_id: instance of PicamCameraID
        """
        return bool(self._NicePicamLib.IsCameraIDConnected(cam_id))

    def is_camera_open_elsewhere(self, cam_id):
        """
        Returns a boolean indicating whether the camera matching cam_id
        is open in another program.

        Parameters
        -------
        cam_id: instance of PicamCameraID
        """
        return bool(self._NicePicamLib.IsCameraIDOpenElsewhere(cam_id))

    def open_first_camera(self, cam_name):
        """
        Opens the first available camera, and assigns it the name 'cam_name'
        """
        ID_array, count = self.get_available_camera_IDs()
        if count == 0:
            raise PicamError('No cameras available - could not open first camera')
        if count ==1:
            id = ID_array
        else:
            id = ID_array[0]
        self.open_camera(id, cam_name)

    def add_camera(self, cam_name, handle, NicePicam):
        """Adds a camera with the name cam_name and handle 'handle' to the
        dictionairy of cameras, self.cameras"""
        if cam_name in self.cameras:
            raise PicamError('Camera name {} already in use'.format(cam_name))
        self.cameras[cam_name] = PicamCamera(cam_name, handle, NicePicam,
                                             self._ffi, self._NicePicamLib, self)

    def open_camera(self, cam_id, cam_name):
        """Opens the camera associated with cam_id, and assigns it the name
        'cam_name'"""
        handle = self._NicePicamLib.OpenCamera(cam_id)
        NicePicam = self._NicePicamLib.NicePicam(handle)
        self.add_camera(cam_name, handle, NicePicam)

    def open_cameras(self, cam_dict):
        IDarray, n = self.get_available_camera_IDs()
        for cam_name in cam_dict.iterkeys():
            for i in range(n):
                if IDarray[i].model == cam_dict[cam_name]:
                    self.open_camera(IDarray[i], i)
                    break
                if i == n-1:
                    raise(PicamError("Camera {} does not exist".format(cam_name)))

    def destroy_rois(self, rois):
        """Releases the memory associated with PicamRois structure 'rois'.

        NOTE: this only works for instances of rois created from
        'getset_rois', and not for user-created rois from 'create_rois'
        """
        self._NicePicamLib.DestroyRois(rois)
