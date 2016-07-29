# -*- coding: utf-8 -*-
"""
Driver Module for Thorlabs CCSXXX series spectrometers.  Currently Windows
only.

Copyright Christopher Rogers 2016
"""
import numpy as np
import time
import sys
from ctypes import (c_char_p, c_int, WinDLL, c_bool, byref, c_double,
                    create_string_buffer, c_int32, c_ulong, c_long)
from visa import ResourceManager, VisaIOError
from nicelib import NiceLib, NiceObjectDef, load_lib
from . import Spectrometer
from ...errors import InstrumentTypeError, Error, InstrumentNotFoundError



if sys.maxsize > 2**32:
    lib = WinDLL('TLCCS_64')
else:
    lib = WinDLL('TLCCS_32')

_SPEC_TYPES = {'0x8081': 'CCS100', '0x8083': 'CCS125', '0x8085': 'CCS150',
               '0x8087': 'CCS175', '0x8089': 'CCS200'}
IDLE = 2
CONT_SCAN = 4
DATA_READY = 16
WAITING_FOR_TRIG = 128
MAX_CALIBRATION_POINTS = 10
ATTR_USER_DATA = c_ulong(0x3FFF0007)
ATTR_CAL_MODE = c_ulong(0x3FFA0000)
NUM_RAW_PIXELS = 3694


def _instrument(params):
    """ Possible params include 'ccs_usb_address', 'ccs_serial_number',
    'ccs_model'.
    """
    if 'ccs_usb_address' in params:
        return get_spectrometer(address=params['ccs_usb_address'])
    elif 'ccs_serial_number' in params:
        return get_spectrometer(serial=params['ccs_serial_number'])
    elif 'ccs_model' in params:
        return get_spectrometer(model=params['ccs_model'])
    raise InstrumentTypeError()


def list_spectrometers():
    """
    Get a list of all spectrometers currently attached.
    """
    spectrometer_list = []
    search_string = "USB?*?{VI_ATTR_MANF_ID==0x1313 && ((VI_ATTR_MODEL_CODE==0x8081) || (VI_ATTR_MODEL_CODE==0x8083) || (VI_ATTR_MODEL_CODE==0x8085) || (VI_ATTR_MODEL_CODE==0x8087) || (VI_ATTR_MODEL_CODE==0x8089))}"
    rm = ResourceManager()
    try:
        raw_spec_list = rm.list_resources(search_string)
    except:
        return spectrometer_list

    for spec in raw_spec_list:
        temp = spec.split("::")
        spec = {'address': spec, "model": _SPEC_TYPES[temp[2]],
                "serial": temp[3]}
        spectrometer_list.append(spec)
    return spectrometer_list


class NiceCCSLib(NiceLib):
    """ Provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.TCube.DCServo.dll"""
    _info = load_lib('tlccs', __package__)
    _struct_maker = None
    _prefix = ('tlccs_')
    _buflen = 256

    init = ('in', 'in', 'in', 'out')
    identificationQuery= ('in', 'buf', 'buf', 'buf', 'buf', 'buf')
    NiceCCS = NiceObjectDef({
        'close': ('in'),
        'setIntegrationTime': ('in', 'in'),
        'getIntegrationTime': ('in', 'out'),
        'startScan': ('in'),
        'startScanCont': ('in'),
        'startScanExtTrg': ('in'),
        'startScanContExtTrg': ('in'),
        'getDeviceStatus': ('in', 'out'),
        'getScanData': ('in', 'arr[{}]'.format(NUM_RAW_PIXELS)),
        'getRawScanData': ('in', 'out'),
        'setWavelengthData': ('in', 'in', 'in', 'in'),
        'getWavelengthData': ('in', 'in', 'arr[{}]'.format(NUM_RAW_PIXELS), 'out', 'out'),
        'getUserCalibrationPoints': ('in', 'out', 'out', 'out'),
        'setAmplitudeData': ('in', 'in', 'in', 'in', 'in'),
        'getAmplitudeData': ('in', 'arr[{}]'.format(NUM_RAW_PIXELS), 'in', 'in', 'in'),
        'identificationQuery': ('in', 'buf[256]', 'buf[256]', 'buf[256]', 'buf[256]', 'buf[256]'),
        'revision_query': ('in', 'out', 'out'),
        'reset': ('in'),
        'self_test': ('in', 'out', 'out'),
        'setUserText': ('in', 'in'),
        'getUserText': ('in', 'out'),
        'setAttribute': ('in', 'in', 'in'),
        'getAttribute': ('in', 'in', 'out'),
        'error_query': ('in', 'out', 'out'),
        'error_message': ('in', 'in', 'buf[512]')
    })


def get_spectrometer(**kwargs):
    """
    Get a spectrometer by attribute. Returns the first attached spectrometer
    that matches the ``\*\*kwargs``. E.g. passing serial='abc' will return a
    spectromer whose serial number is 'abc', or None if no such spectromer
    is connected.
    """
    specrometer_list = list_spectrometers()
    if not specrometer_list:
        raise InstrumentNotFoundError("No spectrometers attached")
    if not kwargs:
        return CCS(specrometer_list[0])

    kwarg = kwargs.items()[0]
    if kwarg[0] not in ['address', 'serial', 'model']:
        raise TypeError("Got an unexpected keyword argument '{}'".format(kwarg[0]))
    for spec in specrometer_list:
        if spec[kwarg[0]] == kwarg[1]:
            return CCS(spec)
    raise InstrumentNotFoundError("No spectrometer found matching the given parameters")


class CCS(Spectrometer):
    """
    A CCS-series Thorlabs spectrometer.  If this construcor is called, it will
    connect to the first available spectrometer (if there is at least one).
    It can also be accessed by calling get_spectrometer using any one of the
    parameters 'address', 'serial', or 'model'.  Calling the function
    :py:func:`~instrumental.drivers.instrument`, using any one of
    the parameters 'spec_usb_address', 'spec_serial_number', or 'spec_model'
    will also return a CCS instance (if successful).
    """
    # TODO: add tlccs_setWavelengthData
    # also, getUserCalibrationPoints, set/getAplitudeData
    def __init__(self, spectrometer_attributes=None):
        """
        Create a spectrometer object by connecting to the spectrometer that
        matches the attributes in spectrometer_attributes (if
        spectrometer_attributes=None, then the first valid CCS spectrometer is
        connected to).
        """
        if spectrometer_attributes is None:
            spectrometer_attributes = self.get_spectrometer()
        self._address = spectrometer_attributes['address']
        self._serial_number = spectrometer_attributes['serial']
        self._model = spectrometer_attributes['model']
        self._handle = c_int()
        self.num_pixels = 3648
        self._data_array = c_double * self.num_pixels
        status = self._open()
        self._ll = LowLevel(self._handle, self.num_pixels)
        self._error_message(status)

        temp = self._ll.get_wavelength_data()
        self._wavelength_array = temp[0]
        self._background = np.zeros((self.num_pixels, 1))
        self.stop_and_clear()

    def __del__(self):
        self.close()

    def _open(self, id_query=True, reset=False):
        """Open a connection to a CCS spectrometer, using the information provided
        when constructing the CCS class.
        The self._handle property is set in this method, which allows access to
        the spectrometer for future method calls
        Parameters
        ----------
        id_query : bool, optional
            This parameter specifies whether an identification query is
            performed during the initialization process.
        resetDevice : bool, optional
            This parameter specifies whether the instrument is reset during the
            initialization process.
        Returns
        -------
        status : int
            The status of the execution of the method - passing this to
            _error_message will print the proper error message (if there was
            an error)
        """
        address = c_char_p(self._address)
        id_query = c_bool(id_query)
        reset = c_bool(not reset)
        status = lib.tlccs_init(address, id_query, reset, byref(self._handle))
        return status

    def close(self):
        """
        Closes the connection to the spectrometer.
        """
        status = lib.tlccs_close(self._handle)
        self._error_message(status)

    def stop_and_clear(self):
        """
        This method stops any scans in progress, and reads (and then discards)
        any data that the spectrometer is waiting to transmit.
        """
        int_time = self._ll.get_integration_time()
        self._ll.set_integration_time(integration_time=0.001)
        self._ll.start_scan()
        time.sleep(0.005)
        while self.is_data_ready():
            self._ll.get_scan_data()
        self._ll.set_integration_time(int_time)

    def get_data(self, integration_time=None, num_avg=1,
                 use_background=False, wait_time=0.01):
        """Returns spectrometer pixel amplitude data (as well as the
        corresponding wavelngths).  The data can be averaged over a number of
        trials 'num_Avg' if desired.  If desired, a backgorund spectra can be
        subtracted from the data.  The stored background spectra can be
        used, or a new background spectra can be taken.
        Parameters
        ----------
        integration_time : float, optional
            This parameter specifies the integration time in seconds.  If the
            parameter is not specified, the current spectrometer integration
            time is used.  The range is specified as being between 1e-5 and 60
            seconds.  Note that in practice, times greater than 50 seconds do
            not seem to work properly.
        num_avg : int, Default=1
            The number of spectra to average over.
        use_background : bool, Default=False
            If true, the spectrometer subtracts the current background spectra
            (stored in self._background) from the data.
        wait_time : float
            The time in seconds the method waits between checking whether the
            spectrometer is ready with data.  This parameter should not
            normally need to be adjusted.
        Returns
        -------
        data : numpy array of float of size (self.num_pixels, 1)
            The amplitude data from the spectrometer, given in arbitrary units.
        wavelength_data : numpy array of float of size (self.numpixel, 1)
            The wavelength (in nm) corresponding to each pixel.
        """
        saturated = False
        self.stop_and_clear()
        if integration_time > 0:
            self._ll.set_integration_time(integration_time)
        data = np.zeros((self.num_pixels, 1))

        self._ll.start_cont_scan()
        for i in range(num_avg):
            while not self.is_data_ready():
                time.sleep(wait_time)
            temp = self._ll.get_scan_data()
            data = data + temp
            if sum(temp >= (1.0 - 1e-5))[0]:
                saturated = True

        self.stop_and_clear()
        data = data/num_avg
        if saturated:
            pass
        if use_background:
            data = data-self._background
        return [data, self._wavelength_array]

    def set_background(self, integration_time=None, num_avg=1, wait_time=0.01):
        """Collects a spectrum with the given settings, and then sets this as
        the background spectrum.  Both the integration time and the number of
        spectra to average over can be set using the relevant paramters.  The
        stored spectrum can be accessed as self._background.
        Parameters
        ----------
        integration_time : float
            The integration time, in seconds, of the spectra used to creat the
            background spectra.  If not given, the integration time currently
            set on the spectrometer is used.
        num_avg : int
            The number of spectra to average over when creating the background
            spectrum.  The default is 1 (no averaging).
        wait_time : float
            The time in seconds the method waits between checking whether the
            spectrometer is ready with data.  This parameter should not
            normally need to be adjusted.
        """
        if integration_time > 0:
            self._ll.set_integration_time(integration_time)
        self._background, _ = self.get_data(num_avg=num_avg, wait_time=wait_time)

    def calibrate_wavelength(self, wavelength_array, pixel_array, num_points,
                             reset=False):
        """This function sets a custom pixel-wavelength calibration on the
        spectrometer.  The data points are used to interpolate the array
        returned when calling 'get_scan_data'.  Note that the given values
        must be strictly increasing as a function of wavelength, and that
        numpoionts must be between 4 and 10 (inclusive).
        Parameters
        ----------
        num_points : int
            The number of data points to be used in the interpolation.  Must be
            between 4 and 10.
        pixel_data : array of int
            The pixel indices for the interpolation.
        wavelength_data : array of float
            The wavelengths (in nm) to be used in the interpolation.
        reset : bool
            If True, set the self._wavelength_array to the factory setting, in
            which case the other parameters are ignored Otherwise, the array is
            set according the spectrometer's interpolation of the given
            calibration points.
        """
        if reset:
            self._wavelength_array = self._ll.get_wavelength_data()
        else:
            self._ll.set_wavelength_data(num_points, pixel_array, wavelength_array)
            self._wavelength_array = self._ll.get_wavelength_data(data_set=True)

    def is_idle(self):
        """
        Returns 'True' if the spectrometer is idle
        """
        status = self._ll.get_status()
        if 'idle' in status:
            return True
        else:
            return False

    def is_data_ready(self):
        """
        Returns 'True' if the spectrometer is ready to transmit data from a
        scan.
        """
        status = self._ll.get_status()
        if 'data_ready' in status:
            return True
        else:
            return False

    def waiting_for_trig(self):
        """
        Returns 'True' if the spectrometer armed to start a new scan and is
        waiting for an external trigger signal.
        """
        status = self._ll.get_status()
        if 'waiting_for_trig' in status:
            return True
        else:
            return False

    def cont_scan_in_progress(self):
        """
        Returns 'True' if a continuous scan is in progress
        """
        status = self._ll.get_status()
        if 'cont_scan_in_progress' in status:
            return True
        else:
            return False

    def _error_message(self, status):
        self._ll.error_message(status)


class LowLevel():
    """
    Contains lower level functions for communicating with the spectrometer
    """
    def __init__(self, handle, num_pixels):
        self._handle = handle
        self.num_pixels = num_pixels
        self._data_array = c_double * self.num_pixels

    def get_attribute(self, attribute):
        """
        Returns the specified attribute, which can be 'user_data' or 'cal_mode.
        If attribute is 'cal_mode', then return value of 0 indicates that user
        data is being used, while  a return value of 1 indicates that
        Thorlabs data is being used.
        """
        if attribute == 'user_data':
            attribute = ATTR_USER_DATA
        elif attribute == 'cal_mode':
            attribute = ATTR_CAL_MODE
        else:
            raise Error('Invalid Attribute in get_attribute')
        state = c_ulong()
        status = lib.tlccs_getAttribute(self._handle, attribute, byref(state))
        self.error_message(status)
        return state.value

    def set_attribute(self, attribute, state):
        """
        Sets the spectrometer's 'user_data' attribute to 'state'.
        """
        if attribute == 'user_data':
            attribute = ATTR_USER_DATA
        else:
            raise Error('Invalid Attribute in set_attribute')
        state = c_long(state)
        status = lib.tlccs_setAttribute(self._handle, attribute, state)
        self.error_message(status)

    def set_wavelength_data(self, num_points, pixel_data, wavelength_data):
        """This function sets a custom pixel-wavelength correlation on the
        spectrometer.  The data points are used to interpolate the array
        returned when calling 'get_wavelength_data'.  Note that the given
        values must be strictly increasing as a function of wavelength, and
        that num_points must be between 4 and 10 (inclusive).
        Parameters
        ----------
        num_points : int
            The number of data points to be used in the interpolation.  Must be
            between 4 and 10.
        pixel_data : array of int
            The pixel indices for the interpolation.
        wavelength_data : array of float
            The wavelengths (in nm) to be used in the interpolation.
        """
        if num_points < 4 or num_points > 10:
            raise Error('Invalid number of data points in set_wavelength_data')
        pixels = c_int32 * num_points
        pixels = pixels()
        wavelengths = c_double * num_points
        wavelengths = wavelengths()
        for i in range(num_points):
            pixels[i] = c_int32(pixel_data[i])
            wavelengths[i] = c_double(wavelength_data[i])
        num_points = c_int32(num_points)

        status = lib.tlccs_setWavelengthData(self._handle, pixels, wavelengths,
                                             num_points)
        self.error_message(status)

    def get_calibration_points(self):
        """This function gets the user-defined calibration points used to set
        the current custom pixel-wavelength correlation.  The pixel indices,
        corresponding wavelengths and the number of points are returned.
        Returns
        ----------
        pixel_data : array of int
            The pixel indices of the calibration data.
        wavelength_data : array of float
            The wavelengths (in nm) of the calibration data.
        num_points : int
            The number of data points in the calibration data.
        """
        pixel_data = c_int32 * MAX_CALIBRATION_POINTS
        pixel_data = pixel_data()
        wavelength_data = c_double * MAX_CALIBRATION_POINTS
        wavelength_data = wavelength_data()
        num_points = c_int32()
        status = lib.tlccs_getUserCalibrationPoints(self._handle, byref(pixel_data),
                                                    byref(wavelength_data), byref(num_points))
        self.error_message(status)
        wavelength_array = self.convert_c_double_array(wavelength_data)
        num_points = num_points.value
        wavelength_array = wavelength_array[0:num_points]
        pixel_array = np.zeros((num_points, 1), dtype=int)
        for i in range(num_points):
            pixel_array[i] = pixel_data[i]
        return [pixel_array, wavelength_array, num_points]

    def set_amplitude_data(self, correction_factors, num_points=None,
                           start_index=0, mode='store'):
        """Sets the amplitude correction factors.  These are factors which
        multiply the pixels intensities, in order to correct for variations
        between pixels.  On start-up, these are all set to unity.  They can be
        changed by sending user-defined factors to the spectrometer.  The array
        correction_factors contains the factors to be set, starting with pixel
        start_index, and continuing on for a number of pixels set by
        num_points.  Default behavior is to set correction values for all
        pixels, in which case correction_factors would be of length 3648.
        Note that setting these values did not seem to alter the values being
        returned by get_scan_data, despite the fact that one could query
        the correction factors using get_amplitude_data and see that they had
        in fact been set properly.
        Paramters
        ---------
        correction_factors : array of float
            Correction factors for the pixels.
        num_points : int
            The number of pixels to apply the correction factors (typically the
            length of correction_factors).
        start_index : int
            The index of the first pixel to which the correction factors
            will be applied.
        mode : str
            This parameter can be either 'store' or 'one_time'.  If set to
            'one_time', the correction factors are only applied to the current
            data.  If set to 'store', the correction factors will be applied to
            the current data and all future data (until the factors are set
            again, or the spectrometer is reset).
        """
        if not num_points:
            num_points = self.num_pixels
        if (num_points + start_index) > self.num_pixels:
            raise Error('Invalid combination of start_index and num_points in set_amplitude_data')
        if mode == 'one_time':
            mode = c_int32(1)
        elif mode == 'store':
            mode = c_int32(2)
        else:
            raise Error('Invalid mode selected in set_amplitude_data')
        factors = c_double * num_points
        factors = factors()
        for i in range(num_points):
            factors[i] = c_double(correction_factors[i])
        num_points = c_int32(num_points)
        start_index = c_int32(start_index)
        status = lib.tlccs_setAmplitudeData(self._handle, factors, num_points,
                                            start_index, mode)
        self.error_message(status)

    def get_amplitude_data(self, num_points=None, start_index=0,
                           mode='stored'):
        """Gets the amplitude correction factors.  These are factors which
        multiply the pixels intensities, in order to correct for variations
        between pixels.  On start-up, these are all set to unity.  The array
        correction_factors returns the factors, starting with pixel
        start_index, and continuing on for a number of pixels set by
        num_points.  Default behavior is to return values for all
        pixels, in which case correction_factors would be of length 3648.
        Paramters
        ---------
        num_points : int
            The number of pixels for which to get the correction factors.
        start_index : int
            The index of the first pixel for which to get the correction
            factors.
        mode : str
            This parameter can be either 'stored' or 'one_time'.  If set to
            'one_time', the correction factors for the current data are
            returned.  If set to 'stored', the correction factors stored in
            the spectrometers non-volatile memory will be returned.
        Returns
        -------
        correction_factors : array of float
            Array of pixel correction factors, of length num_points.
        """
        if not num_points:
            num_points = self.num_pixels
        if (num_points + start_index) > self.num_pixels:
            raise Error('Invalid combination of start_index and num_points in get_amplitude_data')
        if mode == 'one_time':
            mode = c_int32(1)
        elif mode == 'stored':
            mode = c_int32(2)
        else:
            raise Error('Invalid mode selected in get_amplitude_data.')
        factors = c_double * num_points
        factors = factors()
        num_points = c_int32(num_points)
        start_index = c_int32(start_index)
        status = lib.tlccs_getAmplitudeData(self._handle, byref(factors),
                                            start_index, num_points, mode)
        correction_factors = self.convert_c_double_array(factors)
        self.error_message(status)
        return correction_factors

    def set_integration_time(self, integration_time):
        """Sets the integration time property of the spectrometer, in seconds.
        Note that when the spectrometer is initialized or reset, the default
        integration time of 1e-3 seconds is set.
        Note also that this cancels any single, continuous and/or triggered
        scans that had been in progress.
        Parameters
        ----------
        integration_time : float
            This parameter specifies the integration time in seconds.  The
            range is specified as being between 1e-5 and 60 seconds.  Note that
            in practice, times greater than 50 seconds did not seem to work
            properly.
        """
        integration_time = c_double(integration_time)
        status = lib.tlccs_setIntegrationTime(self._handle, integration_time)
        self.error_message(status)

    def get_integration_time(self):
        """Returns the current integration time of the spectrometer, in seconds.
        Note that this cancels any single, continuous and/or triggered scans
        that had been in progress.
        Returns
        -------
        integration_time : float
            This parameter specifies the integration time in seconds.
        """
        integration_time = c_double(0)
        status = lib.tlccs_getIntegrationTime(self._handle,
                                              byref(integration_time))
        self.error_message(status)
        return integration_time.value

    def start_scan(self):
        """Starts a scan.
        Note that this cancels any single, continuous and/or triggered scans
        that had been in progress. Note also that this function returns almost
        immediately after starting the scan - that is, it does not wait untill
        the scan is finished to return.
        """
        status = lib.tlccs_startScan(self._handle)
        self.error_message(status)

    def start_cont_scan(self):
        """Starts a continuous scan - scans oif length integration time are
        repeated continuously.
        Note that this cancels any single, continuous and/or triggered scans
        that had been in progress.
        """
        status = lib.tlccs_startScanCont(self._handle)
        self.error_message(status)

    def start_scan_trg(self):
        """Arms the spectrometer for a triggered scan, meaning that it will
        wait for a signal from the external trigger before executing a single
        scan.  This function returns immediately, and does not wait for the
        trigger or for the scan to finish.
        Note that this cancels any single, continuous and/or triggered scans
        that had been in progress.
        """
        status = lib.tlccs_startScanExtTrg(self._handle)
        self.error_message(status)

    def start_cont_scan_trg(self):
        """Arms the spectromter for a constinuous triggered scan, meaning that
        it will wait for a signal from the external trigger before executing a
        scan, and will then rearm immediatley after that scan has completed,
        and so on.
        Note that this function returns immediately, and does not wait for the
        trigger or for the scan to finish.
        Note also that this cancels any single, continuous and/or triggered
        scans that had been in progress.
        """
        status = lib.tlccs_startScanContExtTrg(self._handle)
        self.error_message(status)

    def get_scan_data(self):
        """This method reads out the processed scan data.
        Note that when the raw scan data is overexposed, the scan returns an
        error and all data points are set to zero (0.0).
        Returns
        -------
        data : array of type float, of length self.num_pixels = 3648
            Array containing the processed pixel values from the last completed
            scan.
        """
        data = self._data_array(0)
        status = lib.tlccs_getScanData(self._handle, byref(data))
        self.error_message(status)

        data = self.convert_c_double_array(data)
        return data

    def _get_raw_scan_data(self):
        """This function reads out the raw scan data.
        Returns
        -------
        sacn_data : array of type int, of length NUM_RAW_PIXELS = 3648
            Array containing the raw pixel values from the last completed
            scan.
        """
        data = c_int * NUM_RAW_PIXELS
        data = data()
        status = lib.tlccs_getRawScanData(self._handle, byref(data))
        self.error_message(status)

        scan_data = np.zeros((NUM_RAW_PIXELS, 1), int)
        for i in range(NUM_RAW_PIXELS):
            scan_data[i] = data[i]
        return scan_data

    def get_wavelength_data(self, data_set=False):
        """This function returns data for the wavelength corresponding to each
        pixel (in nm).  It also returns the minimum and maximum wavelengths.
        Note that calling this method cancels any scan that had been in
        progress.
        Note also that when the raw scan data is overexposed, the scan returns
        an error and all data points are set to zero (0.0).
        Parameters
        ----------
        data_set : bool, optional, default = False
            If False, the factory adjustment data is used to generate the
            wavelength array.  If True, user-defined adjustment data is used
        Returns
        -------
        wavelength_data : array of type c_double, of length self.num_pixels
            Array containing the wavelength corresponding to each pixel (in nm)
            for the specifed data set.
        min_wavelength : float
            Minimum wavelength for the specified data set (in nm).
        maximum_wavelenth : float
            Maximum wavelength for the specified data set (in nm).
        """
        wavelength_data = self._data_array(0)
        data_set = c_bool(data_set)
        min_wavelength = c_double(0)
        max_wavelength = c_double(0)
        status = lib.tlccs_getWavelengthData(self._handle, data_set, byref(wavelength_data), byref(min_wavelength), byref(max_wavelength))
        self.error_message(status)

        wavelength_data = self.convert_c_double_array(wavelength_data)
        return [wavelength_data, min_wavelength.value, max_wavelength.value]

    def convert_c_double_array(self, array):
        """
        This method converts an array of type ctypes.c_double into a numpy
        array, and returns that numpy array.
        """
        n = len(array)
        data = np.zeros((n, 1))
        for i in range(n):
            data[i] = float(array[i])
        return data

    def get_status(self, status=None):
        """Returns a list instance containing strings indicating the status of
        the device.
        Parameters
        ----------
        status : int, optional
        An int representing the state of the byte register.  If 'None'
        (default), the method gets the current status directly from the
        spectrometer.
        """
        status_list = []
        if status is None:
            status = self._get_device_status()
        status = status % 256
        if status//WAITING_FOR_TRIG:
            status_list.append('waiting_for_trig')
        status = status % 32
        if status//DATA_READY:
            status_list.append('data_ready')
        status = status % 8
        if status//CONT_SCAN:
            status_list.append('cont_scan_in_progress')
        status = status % 4
        if status//IDLE:
            status_list.append('idle')
        return status_list

    def _get_device_status(self):
        """Returns, as an integer, the result of querying the byte status
        register.
        From what I could tell:
        1 -> This is always on, and does not seem to indicate anything
        2 -> There is no scan in progress, and no data waiting to be
        transferred.
        4 -> Something to do with a continuous scan being in progress
        8 -> Never is on.
        16 -> Scan data is ready to be read.
        64 -> Never on.
        128 -> Waiting for a trigger
        256 -> Something to do with a continuous scan.
        512 -> Something to do with a continous triggered scan.
        The documentation give the table below, but note that 4 is definitely
        NOT on when a single scan is in progress, despite what is said here:
        2 -> CCS waits for new scan to execute
        4 -> scan in progress
        8 -> scan starting
        16 -> scan is done, waiting for data transfer to PC
        128 -> same as IDLE except that external trigger is armed
        """
        device_status = c_int32()
        status = lib.tlccs_getDeviceStatus(self._handle, byref(device_status))
        self.error_message(status)
        return device_status.value

    def id_query(self):
        """Returns as strings various device identification information
        Note that calling this method cancels any scan that had been in
        progress.
        Returns
        -------
        manufacturer : string
            The manufacturer name.
        device_name : string
            The device name.
        serial_number : string
            The serial number of the device.
        firmware_version : string
            The firware version number.
        driver_version : string
            The driver version number.
        """
        manufacturer = create_string_buffer('\000' * 256)
        device_name = create_string_buffer('\000' * 256)
        serial_number = create_string_buffer('\000' * 256)
        firmware_version = create_string_buffer('\000' * 256)
        driver_version = create_string_buffer('\000' * 256)
        status = lib.tlccs_identificationQuery(self._handle, manufacturer, device_name, serial_number, firmware_version, driver_version)
        self.error_message(status)
        return [manufacturer.value, device_name.value, serial_number.value,
                firmware_version.value, driver_version.value]

    def reset(self):
        """
        Resets the device.
        """
        status = lib.tlccs_reset(self._handle)
        self.error_message(status)

    def error_message(self, status):
        if status < 0:
            raise Error(VisaIOError(status).message)
    