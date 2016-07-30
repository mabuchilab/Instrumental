# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 12:21:01 2015

@author: Lab

Copyright 2015 Christopher Rogers

Class to control Princeton Instruments Cameras using the PICAM SDK

Note that one needs to install PICAM from the Princeton Instruments ftp site,
and then copy .dlls to the current working directory, or some other directory
on the path.

Also, make sure to not mix .dlls and headers from different PICAM releases ...
"""

from ctypes import CDLL, pointer, POINTER, c_char, c_bool, c_float
from ctypes import c_char_p, cast, Structure, c_int
from ctypes import c_byte, c_int8, c_uint8, c_int16, c_uint16, c_int32, c_uint
from ctypes import c_uint32, c_int64, c_uint64, c_double, c_void_p
from ctypes import create_string_buffer, byref, addressof, c_uint, cast, string_at, wstring_at
from ctypes.wintypes import DWORD, INT, ULONG, DOUBLE, HWND
from numpy import frombuffer, log2, zeros, sum
from matplotlib.pyplot import figure, show, imshow, cm, subplots, axes, subplots_adjust, sca, draw, pause, cla
from matplotlib.widgets import Slider, Button, RadioButtons
from matplotlib import interactive
from time import sleep
import os.path
from PICAMheader import *
from pyCamStructs import picam_acquisition_error, picam_error, PyCamError

lib = CDLL('Picam')


class pyCAM():
    """
    A  class for Princeton Instruments Cameras.  Multiple cameras can be opened
    within the same class.  Opening multiple instances of this class at the
    same time may not work.
    """
    def __init__(self, cam_dict={}):
        """
        Attempt to connect to any camera models given in the iterable cam_model

         Parameters
        ----------

        cam_dict : dictionairy of cameras to open
            The items are the integers corresponding to the models of the
            cameras to be opened.  These can be found in the header file.  The
            keys are the camera names.
        """
        self.initialize_library()
        self.picam_dll_version = self.picam_GetVersion()
        self.cameras = {}
        self.rois_dict = {}
        self.displays = {}
        self.open_cameras(cam_dict)
        self.keep_alive_roi_dict = {}

    def initialize_library(self):
        """
        Initializes the Picam dll library
        """
        initialized = pibln(False)
        error = lib.Picam_IsLibraryInitialized(pointer(initialized))
        picam_error(error)
        if bool(initialized) is False:
            error = lib.Picam_InitializeLibrary()
            picam_error(error)

    def uninitialize_library(self):
        """
        un-initializes the Picam dll library
        """
        error = lib.Picam_UninitializeLibrary()
        picam_error(error)

    def close(self):
        self.__exit__()

    def __exit__(self):
        for cam_name in self.cameras.keys():
            self.close_camera(cam_name)
            print 'closed camera {}'.format(cam_name)
        self.uninitialize_library()

    def get_enumeration_string(self, enumeration_type, value):
        """
        Returns the string of the associated with the enum 'value' of type
        'enumeration type'
        """
        string = c_char_p()
        error = lib.Picam_GetEnumerationString(c_uint8(enumeration_type),
                                               c_int(value), byref(string))
        picam_error(error)
        value = string.value
        self.picam_DestroyString(string)
        return value

    def picam_DestroyString(self, s):
        """
        Destroys the memory associated with string s
        """
        error = lib.Picam_DestroyString(s)
        picam_error(error)

    def picam_DestroyCameraIDs(self, cam_id):
        """
        Destroys the memory associated with string the picam_id 'cam_id'
        """
        error = lib.Picam_DestroyCameraIDs(cam_id)
        picam_error(error)
        return

    def is_demo_camera(self, cam_id):
        """
        Returns a boolean indicating whether the camera corresponding to
        cam_id is a demo camera
        """
        isDemo = pibln()
        error = lib.Picam_IsDemoCamera(byref(cam_id), pointer(isDemo))
        picam_error(error)
        return isDemo.value

    def picam_GetVersion(self):
        """
        Returns a string containing version information for the Picam dll
        """
        major = piint()
        minor = piint()
        distribution = piint()
        release = piint()
        error = lib.Picam_GetVersion(pointer(major), pointer(minor),
                                     pointer(distribution), pointer(release))
        picam_error(error)
        release = str(release.value)
        temp = (major.value, minor.value, distribution.value, release[0:2],
                release[2:4])
        version = '{0[0]}.{0[1]}.{0[2]} released in 20{0[3]}-{0[4]}'
        return version.format(temp)

    def connect_demo_camera(self, model, serial_number):
        """
        Connects a demo camera of the specified model and serial number. Note
        that 'connecting' a demo camera is not the same as 'opening' a demo
        camera.  Connecting a demo camera is equivalent to physically
        connecting a real camera to your pc.

        Parameters
        ----------

        model :int
            corresponds to the model of the cameras to be created.  These
            values can be found in the header file.
        serial_number:str

        Returns
        -------
        picam_id: instance of PicamCameraID
            id of the created camera
        """
        picam_id = PicamCameraID()
        connect = lib.Picam_ConnectDemoCamera
        error = connect(c_int(model), c_char_p(serial_number), byref(picam_id))
        picam_error(error)
        return picam_id

    def get_available_demo_camera_models(self):
        """
        Returns an array of all demo camera models that it is possible to
        create, and the length of that array.
        """
        models = POINTER(PicamModel)()
        count = piint()
        get = lib.Picam_GetAvailableDemoCameraModels
        error = get(byref(models), byref(count))
        picam_error(error)
        # models = [int(models_p[i]) for i in range(0, count.value)]
        return models, count.value

    def disconnect_demo_camera(self, cam_id):
        """
        Disconnects the demo camera specified by cam_id
        """
        error = lib.Picam_DisconnectDemoCamera(cam_id)
        picam_error(error)
        return

    def destroy_models(models):
        """
            Releases memory associated with the array of cam_models 'models'
        """
        error = lib.Picam_DestroyModels(models)
        picam_error(error)
        return

    def get_available_camera_IDs(self):
        """
        Returns an array of cameras that it is currently possible to
        connect to.

        Returns
        -------
        ID_array: array of PicamCameraID
            ids of the available cameras
        count: int
            the number of available cameras
        """
        count = piint()
        ID_array = POINTER(PicamCameraID)()
        error = lib.Picam_GetAvailableCameraIDs(byref(ID_array), byref(count))
        picam_error(error)
        return ID_array, count.value

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
        count = piint()
        ID_array = POINTER(PicamCameraID)()
        error = lib.Picam_GetAvailableCameraIDs(byref(ID_array), byref(count))
        picam_error(error)
        return ID_array, count.value

    def is_cameraID_connected(self, cam_id):
        """
        Returns a boolean indicating whether the camera matching cam_id is
        connected.

        Parameters
        -------
        cam_id: instance of PicamCameraID
        """
        connected = pibln()
        error = lib.Picam_IsCameraIDConnected(cam_id, byref(connected))
        picam_error(error)
        return connected.value

    def is_camera_open_elsewhere(self, cam_id):
        """
        Returns a boolean indicating whether the camera matching cam_id
        is open in another program.

        Parameters
        -------
        cam_id: instance of PicamCameraID
        """
        open_elsewhere = pibln()
        error = lib.Picam_IsCameraIDConnected(cam_id, byref(open_elsewhere))
        picam_error(error)
        return open_elsewhere.value

    def destroy_handles(self, handle):
        """
        Releases the memory associated with the camera handle or array of
        camera handles 'handle'
        # This function is currently not working
        """
        array = (PicamHandle * 1)()
        array[0] = handle
        error = lib.Picam_DestroyHandles(byref(handle))
        picam_error(error)
        return

    def open_first_camera(self, cam_name):
        """
        Opens the first available camera, and assigns it the name 'cam_name'
        """
        handle = PicamHandle()
        error = lib.Picam_OpenFirstCamera(byref(handle))
        picam_error(error)
        self.add_camera(cam_name, handle)
        return

    def add_camera(self, cam_name, handle):
        """Adds a camera with the name cam_name and handle 'handle' to the
        dictionairy of cameras, self.cameras"""
        self.name_in_use_error(cam_name)
        self.cameras[cam_name] = handle
        self.rois_dict[cam_name] = self.getset_rois(cam_name)

    def name_in_use_error(self, cam_name):
        """ Raises an Exception if the given camera cam_name is already in
        use"""
        if cam_name in self.cameras:
            error_string = "camera name {} is already in use"
            raise(PyCamError(error_string.format(cam_name)))

    def name_DNE_error(self, cam_name):
        """ Raises an Exception if the given camera cam_name does not exist"""
        if not (cam_name in self.cameras):
            error_string = "camera name {} does not exist"
            raise(PyCamError(error_string.format(cam_name)))

    def open_camera_from_id(self, cam_id, cam_name):
        """Opens the camera associated with cam_id, and assigns it the name
        'cam_name'"""
        handle = PicamHandle()
        error = lib.Picam_OpenCamera(byref(cam_id), pointer(handle))
        print error
        picam_error(error)
        self.add_camera(cam_name, handle)
        return

    def open_cameras(self, cam_dict):
        IDarray, n = self.get_available_camera_IDs()
        for cam_name in cam_dict.iterkeys():
            for i in range(n):
                if IDarray[i].model == cam_dict[cam_name]:
                    self.open_camera_from_id(IDarray[i], cam_name)
                    break
                if i == n-1:
                    text = "Camera {} not availble"
                    raise(PyCamError(text.format(cam_name)))

    def close_camera(self, cam_name=None):
        """Closes the camera with name 'cam_name'"""
        handle = self.getHandle(cam_name)
        error = lib.Picam_CloseCamera(handle)
        picam_error(error)
        self.cameras.pop(cam_name)
        return

    def get_open_cameras(self):
        """Returns an array of the handles of open cameras, and the number of
        open cameras"""
        count = piint()
        handles = POINTER(PicamHandle)()
        error = lib.Picam_GetOpenCameras(byref(handles), byref(count))
        picam_error(error)
        return handles, count.value

    def is_camera_connected(self, cam_name=None):
        """Returns a boolean indicating whether the camera cam_name is
        connected"""
        handle = self.getHandle(cam_name)
        connected = pibln()
        error = lib.Picam_IsCameraConnected(handle, byref(connected))
        picam_error(error)
        return connected.value

    def get_cameraID(self, cam_name=None):
        """Returns the PicamID structure for the camera with name cam_name"""
        handle = self.getHandle(cam_name)
        cam_id = PicamCameraID()
        error = lib.Picam_GetCameraID(handle, byref(cam_id))
        picam_error(error)
        return cam_id

    def getHandle(self, cam_name=None):
        """Returns the handle of the camera cam_name"""
        if cam_name is None:
            handles = cameras.values()
            if len(handles) == 0:
                text = "Could not return a handle because no cameras are open"
                raise(PyCamError(text))
            return handles[0]

        self.name_DNE_error(cam_name)
        handle = self.cameras[cam_name]
        return handle

    def destroy_firmware_details(self, firmware):
        """Releases the memory associated with the firmware details
        'firmware'"""
        error = lib.Picam_DestroyFirmwareDetails(firmware)
        picam_error(error)
        return

    def get_firmware_details(self, cam_id):
        """Returns the firmware details for the camera cam_id"""
        count = piint()
        firmware_array = POINTER(PicamFirmwareDetail)()
        error = lib.Picam_GetFirmwareDetails(cam_id, byref(firmware_array),
                                             byref(count))
        picam_error(error)
        return firmware_array, count.value

    def _raw_acquire(self, cam_name, readout_count, readout_timeout):
        """Starts and waits for an acquire, and returns the array 'availble',
        which contains information about the available data"""
        handle = self.getHandle(cam_name)
        count = pi64s(readout_count)
        timeout = piint(readout_timeout)
        acquisition_error = PicamAcquisitionErrorsMask()
        available = PicamAvailableData()
        error = lib.Picam_Acquire(handle, count, timeout, byref(available),
                                  byref(acquisition_error))
        picam_error(error)
        picam_acquisition_error(acquisition_error)
        return available

    def acquire(self, cam_name, readout_count, readout_timeout=-1):
        """ returns the handle to an array of the data for a given acquire
        sequence

        Parameters
        ----------

        readout_count: int
            number of readouts to aquire
        readout_timeout: int
            time in ms to wait for a single readout (-1 -> wait forever)
        """
        available = self._raw_acquire(cam_name, readout_count, readout_timeout)
        readout_stride = self.get_readout_stride(cam_name)
        # I'm not sure why, but the first entry is always zero ..., so I added
        # the '+1'
        data_type = c_uint16 * (readout_stride/2 * available.readout_count+1)
        return data_type.from_address(available.initial_readout)

    def start_acquisition(self, cam_name):
        """ This function begins an acquisition and returns immediately (before
        the aqcuisition is completed).

        The number of readouts is set by the camera parameter ReadoutCount
        """
        handle = self.getHandle(cam_name)
        error = lib.Picam_StartAcquisition(handle)
        picam_error(error)
        return

    def stop_acuisition(self, cam_name):
        """Stops a currently running acuisition"""
        handle = self.getHandle(cam_name)
        error = lib.Picam_StopAcquisition(handle)
        picam_error(error)
        return

    def is_aqcuisition_running(self, cam_name):
        """Returns a boolean indicating whether an aqcuisition is currently
        running"""
        handle = self.getHandle(cam_name)
        running = pibln()
        error = lib.Picam_IsAcquisitionRunning(handle, byref(running))
        picam_error(error)
        return running.value

    def wait_for_aqcuisition_update(self, cam_name, time_out=1):
        """ Waits for a readout
        """
        handle = self.getHandle(cam_name)
        time_out = piint(time_out)
        available = PicamAvailableData()
        status = PicamAcquisitionStatus()
        waitFor = lib.Picam_WaitForAcquisitionUpdate
        error = waitFor(handle, time_out, byref(available), byref(status))
        if error == PicamErrorTimeOutOccurred == 32:
            available = None
            status = None
        else:
            picam_error(error)
        return error, available, status

    def get_data_from_available(self, cam_name, available):
        """Returns an array of data corresponding to the data buffer given
        by the PicamAvailableData structure
        """
        readout_stride = self.get_readout_stride(cam_name)
        readout_count = available.readout_count
        # I'm not sure why, but the first entry is always zero ..., so I added
        # the '+1'
        data_type = c_uint16 * (readout_stride/2 * readout_count+1)
        c_data = data_type.from_address(available.initial_readout)

        shapes = self.get_frame_shapes(cam_name)
        x_pixels, y_pixels = shapes[0]
        n_tot = readout_count*y_pixels*x_pixels
        pixel_tot = y_pixels*x_pixels

        temp_data = frombuffer(c_data, c_uint16)
        temp_data = temp_data[1:(n_tot+1)]
        # When not binned, the very last pixel doesn't seem to work correctly
        if temp_data[n_tot-1] == 0:
            print "Warning: Data was missing the last pixel"
            # messing with this causes errors when shutting down
            # temp_data[n_tot-1] = temp_data[n_tot-2]
        data = zeros((readout_count, y_pixels, x_pixels), int)
        for i in range(readout_count):
            temp_i = temp_data[(pixel_tot*i):(pixel_tot*(i+1))]
            data[i, :, :] = temp_i.reshape((y_pixels, x_pixels))
        return data

    def get_data_from_available_list(self, cam_name, available_list):
        """From a list of PicamAvailableData structures, this function returns
        an array containing the data from the readouts

        Note that the readouts must all be of the same shape.
        """
        data_list = []
        N_readouts = 0
        shapes = self.get_frame_shapes(cam_name)
        x_pixels, y_pixels = shapes[0]
        for available in available_list:
            temp_data = self.get_data_from_available(cam_name, available)
            N_readouts = N_readouts + available.readout_count
            data_list = data_list + [temp_data]
        data = zeros((N_readouts, y_pixels, x_pixels))
        n = 0
        for i in range(len(data_list)):
            temp_data = data_list[i]
            N, _, _ = temp_data.shape
            data[n:n+N, :, :] = temp_data[0:N]
            n = n + N
        return data

    def get_available(self, cam_name, time_out=1):
        """Returns the acquisition status and the structure PicamAvailableData

        This function is for asynchronous acquisition"""
        error, available, status = self.wait_for_aqcuisition_update(cam_name,
                                                                    time_out)
        if error == PicamErrorTimeOutOccurred:
            return None, None
        else:
            return status.running, available

    def getParameterValueType(self, cam_name, parameter):
        """Returns the enumerator of type PicamValueType, indicating the data
        type of parameter 'parameter'"""
        handle = self.getHandle(cam_name)
        typ = c_uint()
        error = lib.Picam_GetParameterValueType(handle, parameter, byref(typ))
        picam_error(error)
        typ = typ.value
        if typ == PicamValueType_Enumeration:
            typ = PicamValueType_Integer
        return typ

    def getParameterValue(self, cam_name, parameter):
        """Returns the value of parameter "parameter" for camera cam_name"""
        handle = self.getHandle(cam_name)
        data_type = self.getParameterValueType(cam_name, parameter)
        if data_type == PicamValueType_Rois:
            getParam = lib.Picam_GetParameterRoisValue
            value = POINTER(PicamRois)()
            error = getParam(handle, parameter, byref(value))
            picam_error(error)
            value = value.contents
            return value
        if data_type == PicamValueType_FloatingPoint:
            value = piflt()
            getParam = lib.Picam_GetParameterFloatingPointValue
        elif data_type == PicamValueType_Integer:
            value = pi64s()
            getParam = lib.Picam_GetParameterIntegerValue
        elif data_type == PicamValueType_LargeInteger:
            value = piint()
            getParam = lib.Picam_GetParameterLargeIntegerValue
        error = getParam(handle, parameter, byref(value))
        picam_error(error)
        return value.value

    def setParameterValue(self, cam_name, parameter, value):
        """Sets the value of the parameter 'parameter' to value 'value'"""
        handle = self.getHandle(cam_name)
        data_type = self.getParameterValueType(cam_name, parameter)
        if data_type == PicamValueType_Rois:
            setParam = lib.Picam_SetParameterRoisValue
            value = pointer(value)
        elif data_type == PicamValueType_FloatingPoint:
            value = piflt(value)
            setParam = lib.Picam_SetParameterFloatingPointValue
        elif data_type == PicamValueType_Integer:
            value = pi64s(value)
            setParam = lib.Picam_SetParameterIntegerValue
        elif data_type == PicamValueType_LargeInteger:
            value = piint(value)
            setParam = lib.Picam_SetParameterLargeIntegerValue
        error = setParam(handle, parameter, value)
        picam_error(error)
        return

    def canSetParameterValue(self, cam_name, parameter, value):
        """Returns a boolean indicating whether the parameter 'parameter' can
        be set to value 'value'"""
        handle = self.getHandle(cam_name)
        data_type = self.getParameterValueType(cam_name, parameter)
        if data_type == PicamValueType_Rois:
            canSetParam = lib.Picam_CanSetParameterRoisValue
            value = pointer(value)
        elif data_type == PicamValueType_FloatingPoint:
            value = piflt(value)
            canSetParam = lib.Picam_CanSetParameterFloatingPointValue
        elif data_type == PicamValueType_Integer:
            value = pi64s(value)
            canSetParam = lib.Picam_CanSetParameterIntegerValue
        elif data_type == PicamValueType_LargeInteger:
            value = piint(value)
            canSetParam = lib.Picam_CanSetParameterLargeIntegerValue
        settable = pibln()
        error = canSetParam(handle, parameter, value, byref(settable))
        picam_error(error)
        return settable.value

    def getParameterDefaultValue(self, cam_name, parameter):
        """Returns the default value of parameter 'parameter' for camera
        cam_name"""
        handle = self.getHandle(cam_name)
        data_type = self.getParameterValueType(cam_name, parameter)
        if data_type == PicamValueType_Rois:
            defaultParam = lib.Picam_GetParameterRoisDefaultValue
            value = POINTER(PicamRois)()
            error = defaultParam(handle, parameter, byref(value))
            picam_error(error)
            return value.contents
        if data_type == PicamValueType_FloatingPoint:
            value = piflt()
            defaultParam = lib.Picam_GetParameterFloatingPointDefaultValue
        elif data_type == PicamValueType_Integer:
            value = pi64s()
            defaultParam = lib.Picam_GetParameterLargeIntegerDefaultValue
        elif data_type == PicamValueType_LargeInteger:
            value = piint()
            defaultParam = lib.Picam_GetParameterIntegerDefaultValue
        error = defaultParam(handle, parameter, byref(value))
        picam_error(error)
        return value.value

    def are_parameters_committed(self, cam_name):
        """Returns a boolean indicating whether or not the camera parameters
        are committed"""
        handle = self.getHandle(cam_name)
        committed = pibln()
        error = lib.Picam_AreParametersCommitted(handle, byref(committed))
        picam_error(error)
        return committed.value

    def commit_parameters(self, cam_name):
        """Commits camera parameters for camera cam_name, and returns an array
        of the paramters that were not correctly committed, and the length of
        that array."""
        handle = self.getHandle(cam_name)
        failed_parameters = c_uint()
        count = piint()
        commitParams = lib.Picam_CommitParameters
        error = commitParams(handle, byref(failed_parameters), pointer(count))
        picam_error(error)
        d_type = c_uint * count.value
        array = d_type.from_address(addressof(failed_parameters))
        return array, count.value

    def getset_param(self, cam_name, parameter, value=None, canset=False,
                     default=False):
        """Gets or sets the value of paramter 'parameter' for camera
        cam_name

        If value==None and canset==False, the value of parameter is returned.
        If value is not None and canset==False, the value of parameter is set
        to value.
        If value is not None and canset==True, a boolean indicating whether
        parameter can be set to value is returned.
        If default==False, then the default value of the parameter is returned
        """
        if default:
            return self.getParameterDefaultValue(cam_name, parameter)
        if value is not None:
            settable = self.canSetParameterValue(cam_name, parameter, value)
        if canset is True:
            return settable
        if (value is not None):
            if settable:
                self.setParameterValue(cam_name, parameter, value)
                return
            else:
                raise(PyCamError("Value is not settable"))
                return
        value = self.getParameterValue(cam_name, parameter)
        return value

    def getset_rois(self, cam_name, rois=None, canset=False,
                    default=False):
        param = PicamParameter_Rois
        value = self.getset_param(cam_name, param, rois, canset, default)
        if (rois is not None) and (canset is False):
            if cam_name in self.rois_dict.keys():
                self.destroy_rois(self.rois_dict[cam_name])
            self.rois_dict[cam_name] = self.getset_param(cam_name, param)
        return value

    def create_rois(self, roi_data):
        """ Returns a PicamRois structure created from the data in roi_data.

        roi data should be a list which contains iterable items containing the
        roi data.  Each iterable should be of the form (x, width, x_binning,
        y, height, y_binning).
        """
        N_roi = len(roi_data)
        roi = (PicamRoi * N_roi)()
        for i in range(N_roi):
            roi_i = roi_data[i]
            roi[i].x = roi_i[0]
            roi[i].width = roi_i[1]
            roi[i].x_binning = roi_i[2]
            roi[i].y = roi_i[3]
            roi[i].height = roi_i[4]
            roi[i].y_binning = roi_i[5]

        rois = PicamRois()
        rois.roi_count = N_roi
        rois.roi_array = addressof(roi)

        # A reference to roi is kept active so it will not get garbage
        # collected
        n = len(self.rois_dict)
        self.keep_alive_roi_dict[n] = roi
        return rois

    def destroy_rois(self, rois):
        """Releases the memory associated with PicamRois structure 'rois'.

        NOTE: this only works for instances of rois created from
        'getset_rois', and not for user-created rois from 'create_rois'
        """
        error = lib.Picam_DestroyRois(rois)
        picam_error(error)

    def get_roi_from_rois(self, rois):
        """Returns the PicamRoi structure 'roi' corresponding to the
        PicamRois structure 'rois'"""
        rtype = (PicamRoi * rois.roi_count)
        return rtype.from_address(rois.roi_array)

    def get_frame_shapes(self, cam_name=None, rois=None):
        """Returns a list of tuples, where the tuples correspond to the number
        of x and y pixels in each region of interest contained in rois.

        If rois is None, then the rois for camera cam_name is used
        """
        if rois is None:
            rois = self.rois_dict[cam_name]
        roi_array = self.get_roi_from_rois(rois)
        shapes = []
        for roi in roi_array:
            x = roi.width/roi.x_binning
            y = roi.height/roi.y_binning
            shapes = shapes + [(x, y)]
        return shapes

    def set_single_frame(self, cam_name, width, height, x0=0, y0=0,
                         x_binning=1, y_binning=1):
        """Sets the camera to capture a single ROI on each frame, with the ROI
        given by the input parameters.

        Parameters
        ----------
        width, height: int
        The number of physical x and y pixels, repectively, on the camera to
        include in the frame

        x0, y0: int
        The  (in pixels) of the bottom row and left-most row, respectively, to
        be included in the frame

        x_binning, y_binning: int
        The size of the on-chip pixel binning to be carried out in the x and y
        directions, respectively.  Note that (width-x0) must be an integer
        multiple of x_binning, and that (hieght-y0) must be an integer multiple
        of y_binning
        """
        if ((width-x0) % x_binning) != 0:
            text = "(width-x0) must be an integer multiple of x_binning"
            raise(PyCamError(text))
        if ((height-y0) % y_binning) != 0:
            text = "(height-y0) must be an integer multiple of y_binning"
            raise(PyCamError(text))
        roi_data = [(x0, width, x_binning, y0, height, y_binning)]
        rois = self.create_rois(roi_data)
        self.getset_rois(cam_name, rois)

    def get_readout_rate(self, cam_name, default=False):
        """ Returns the readout rate (in units of 1/s) of camera cam_name,
        given the current settings"""
        parameter = PicamParameter_ReadoutRateCalculation
        rate = self.getset_param(parameter, cam_name, default=default)
        return rate

    def get_readout_time(self, cam_name, default=False):
        """ Returns the readout time (in ms) of camera cam_name, given the
        current settings"""
        param = PicamParameter_ReadoutTimeCalculation
        rate = self.getset_param(cam_name, param, default=default)
        return rate

    def get_readout_stride(self, cam_name, default=False):
        """Returns the readout stride"""
        param = PicamParameter_ReadoutStride
        value = self.getset_param(cam_name, param, default=default)
        return value

    def getset_exposure_time(self, cam_name, exposure=None, canset=False,
                             default=False):
        """Returns or sets the value of the exposure time (in ms) of camera
        cam_name"""
        param = PicamParameter_ExposureTime
        value = self.getset_param(cam_name, param, exposure, canset, default)
        return value

    def getset_adc_gain(self, cam_name, gain=None, canset=False,
                        default=False):
        """Returns or sets the ADC gain for camera cam_name.

        Parameters
        ----------
        gain:int
        For most cameras, 1->low, 2->medium, 3->high
        """
        param = PicamParameter_AdcAnalogGain
        gain = self.getset_param(cam_name, param, gain, canset, default)
        return gain

    def getset_adc_speed(self, cam_name, speed=None, canset=False,
                         default=False):
        """Returns or sets the ADC speed in MHz

        For many cameras, the possible values are very constrained - for
        typical ccd cameras, both 2MHz and 0.1MHz work."""
        param = PicamParameter_AdcSpeed
        value = self.getset_param(cam_name, param, speed, canset, default)
        return value

    def get_temperature_reading(self, cam_name):
        """Returns the temperature of the sensor in degres Centigrade"""
        param = PicamParameter_SensorTemperatureReading
        value = self.getset_param(cam_name, param)
        return value

    def getset_temperature_setpoint(self, cam_name, setpoint=None,
                                    canset=False, default=False):
        """Set or returns the temperature setpoint in degres Centigrade"""
        param = PicamParameter_SensorTemperatureSetPoint
        value = self.getset_param(cam_name, param, setpoint, canset, default)
        return value

    def get_temperature_status(self, cam_name):
        """Returns a string indicating whether the temperature of the sensor
        has stabilized and is locked to the temperature setpoint value"""
        param = PicamParameter_SensorTemperatureStatus
        value = self.getset_param(cam_name, param)
        if value == PicamSensorTemperatureStatus_Locked:
            value = 'Locked'
        if value == PicamSensorTemperatureStatus_Unlocked:
            value = 'Not Locked'
        return value

    def getset_readout_count(self, cam_name, readout_count=None, canset=False,
                             default=False):
        """ Sets the number of readouts for an asynchronous aquire.

        This does NOT affect the number of readouts for self.aqcuire
        """
        param = PicamParameter_ReadoutCount
        value = self.getset_param(cam_name, param, readout_count, canset,
                                  default)
        return value

    def getset_time_stamp(self, cam_name, setting=None, canset=False,
                          default=False):
        """ Controls the timestamp portion of the frame metadata.

        'setting' is an enum PicamTimeStampsMask_(X) """
        param = PicamParameter_TimeStamps
        value = self.getset_param(cam_name, param, setting, canset, default)
        return value

    def getset_shutter_mode(self, cam_name, shutter_mode=None, canset=False,
                            default=False):
        """ Controls the shutter operation mode.

        Shutter mode is an enum PicamShutterTimingMode_(X)"""

        param = PicamParameter_ShutterTimingMode
        value = self.getset_param(cam_name, param, shutter_mode, canset,
                                  default)
        return value

    def open_shutter(self, cam_name):
        """ Opens the shutter """
        shutter_mode = PicamShutterTimingMode_AlwaysOpen
        self.getset_shutter_mode(cam_name, shutter_mode)

    def close_shutter(self, cam_name):
        """ Closes the shutter """
        shutter_mode = PicamShutterTimingMode_AlwaysClosed
        self.getset_shutter_mode(cam_name, shutter_mode)

    def normal_shutter(self, cam_name):
        """ Puts the shutter into normal mode """
        shutter_mode = PicamShutterTimingMode_Normal
        self.getset_shutter_mode(cam_name, shutter_mode)

    def does_parameter_exist(self, cam_name, parameter):
        """Returns a boolean indicating whether the parameter 'parameter'
        exists for camera cam_name"""
        handle = self.getHandle(cam_name)
        parameter = c_uint(parameter)
        does_exist = pibln()
        does_exist = lib.Picam_DoesParameterExist
        error = does_exist(handle, parameter, byref(does_exist))
        picam_error(error)
        return does_exist.value

    def is_parameter_relevant(self, cam_name, parameter):
        """Returns a boolean indicating whether changing the parameter
        'parameter' will affect the behaviour of camera cam_name, given the
        current settings"""
        handle = self.getHandle(cam_name)
        parameter = c_uint(parameter)
        is_relevant = pibln()
        isRelevant = lib.Picam_IsParameterRelevant
        error = isRelevant(handle, parameter, byref(is_relevant))
        picam_error(error)
        return is_relevant.value

    def get_parameter_list(self, cam_name):
        """Returns an array of all the parameters (but not their values) of
        camera cam_name, and the number of parameters"""
        handle = self.getHandle(cam_name)
        params = c_uint()
        count = piint()
        error = lib.Picam_GetParameters(handle, byref(params), pointer(count))
        picam_error(error)
        d_type = c_uint * count.value
        array = d_type.from_address(params)
        return array, count.value

    def get_data(self, cam_name, readout_timeout=-1):
        """Returns a numpy array of the pixel data for the specified camera.

        Note that this only works if there is a single ROI"""
        shapes = self.get_frame_shapes(cam_name)
        x_pixels, y_pixels = shapes[0]
        c_data = self.acquire(cam_name, readout_count=1,
                              readout_timeout=readout_timeout)
        data = frombuffer(c_data, c_uint16)
        # When not binned, the very last pixel doesn't seem to work correctly
        if data[x_pixels*y_pixels] == 0:
            print "Warning: Data was missing the last pixel"
            # messing with this causes errors when shutting down
            # data[x_pixels*y_pixels] = data[x_pixels*y_pixels-1]
        data = data[1:(x_pixels*y_pixels+1)].reshape((y_pixels, x_pixels,))
        return data

    def get_multiple_data(self, cam_name, readout_count, readout_timeout=-1):
        """Returns a numpy array of the pixel data for the specified camera.

        Note that this only works if there is a single ROI"""
        shapes = self.get_frame_shapes(cam_name)
        x_pixels, y_pixels = shapes[0]
        c_data = self.acquire(cam_name, readout_count, readout_timeout)
        n_tot = readout_count*y_pixels*x_pixels
        pixel_tot = y_pixels*x_pixels
        temp_data = frombuffer(c_data, c_uint16)
        temp_data = temp_data[1:(n_tot+1)]
        # When not binned, the very last pixel doesn't seem to work correctly
        if temp_data[n_tot-1] == 0:
            print "Warning: Data was missing the last pixel"
            # messing with this causes errors when shutting down
            # temp_data[n_tot-1] = temp_data[n_tot-2]
        data = zeros((readout_count, y_pixels, x_pixels), int)
        for i in range(readout_count):
            temp_i = temp_data[(pixel_tot*i):(pixel_tot*(i+1))]
            data[i, :, :] = temp_i.reshape((y_pixels, x_pixels))
        return data

    def get_averaged_data(self, cam_name, num_averages, readout_timeout=-1):
        """Returns a numpy array of floating-point pixel data for the specified
        camera, averaged over num_averages exposures.

        Note that this only works if there is a single ROI"""
        data = self.get_multiple_data(cam_name, num_averages, readout_timeout)
        averaged_data = sum(data, 0)
        averaged_data = averaged_data/float(num_averages)
        return averaged_data

    def show_interactive_image(self, cam_name, readout_timeout=-1):
        """Takes and displays an image from camera cam_name"""
        shapes = self.get_frame_shapes(cam_name)
        print cam_name
        print shapes
        x_pixels, y_pixels = shapes[0]
        data = self.get_data(cam_name, readout_timeout)

        interactive(True)
        fig, ax = subplots()
        subplots_adjust(left=0.25, bottom=0.25)
        im = imshow(data, cmap=cm.gray)
        (vmin0, vmax0) = im.get_clim()
        vmin0 = max((vmin0, 1))
        vmax0 = max((vmax0, 1))
        axcolor = 'lightgoldenrodyellow'
        ax_vmin = axes([0.25, 0.1, 0.65, 0.03], axisbg=axcolor)
        ax_vmax = axes([0.25, 0.15, 0.65, 0.03], axisbg=axcolor)
        vmin = Slider(ax_vmin, 'Min', 0, 16, valinit=log2(vmin0))
        vmax = Slider(ax_vmax, 'Max', 0, 16, valinit=log2(vmax0),
                      slidermin=vmin)
        vmin.slidermax = vmax

        def update(val):
            vmin_i = int(2**vmin.val)
            vmax_i = int(2**vmax.val)
            im.set_clim([vmin_i, vmax_i])
            fig.canvas.draw_idle()
        vmin.on_changed(update)
        vmax.on_changed(update)

        key = len(self.displays)
        self.displays[key] = im, fig, vmin, vmax, ax
        return key

    def show_video(self, cam_name, n=5, readout_timeout=-1):
        """Displays 'n' frames of video from camera cam_name"""
        shapes = self.get_frame_shapes(cam_name)
        x_pixels, y_pixels = shapes[0]
        key = self.show_interactive_image(cam_name, readout_timeout)
        im, fig, vmin, vmax, ax, _ = self.displays[key]
        for i in range(n):
            pause(1e-5)
            c_data = self.acquire(cam_name, 1, readout_timeout)
            data = frombuffer(c_data, c_uint16).reshape((x_pixels, y_pixels))
            sca(ax)
            cla()
            im = imshow(data, cmap=cm.gray)

            def update(val):
                vmin_i = int(2**vmin.val)
                vmax_i = int(2**vmax.val)
                im.set_clim([vmin_i, vmax_i])
                fig.canvas.draw_idle()
            vmin.on_changed(update)
            vmax.on_changed(update)
            vmin.set_val(vmin.val)
        self.displays[key] = im, fig, vmin, vmax, ax
        return key