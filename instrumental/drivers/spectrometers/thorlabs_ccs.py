# -*- coding: utf-8 -*-
# Copyright 2016-2017 Christopher Rogers, Nate Bogdanowicz
"""
Driver Module for Thorlabs CCSXXX series spectrometers.  Currently Windows
only.
"""
import time
from enum import Enum
import numpy as np
from visa import ResourceManager
from cffi import FFI
from nicelib import NiceLib, NiceObjectDef, load_lib

from . import Spectrometer
from ..util import check_units, check_enums
from .. import ParamSet
from ...errors import Error
from ... import Q_

_INST_PARAMS = ['serial', 'usb', 'model']
_INST_CLASSES = ['CCS']

IDLE = 2
CONT_SCAN = 4
DATA_READY = 16
WAITING_FOR_TRIG = 128
NUM_RAW_PIXELS = 3648
BYTES_PER_DOUBLE = 8

ffi = FFI()


def list_instruments():
    """
    Get a list of all spectrometers currently attached.
    """
    paramsets = []
    search_string = "USB?*?{VI_ATTR_MANF_ID==0x1313 && ((VI_ATTR_MODEL_CODE==0x8081) || (VI_ATTR_MODEL_CODE==0x8083) || (VI_ATTR_MODEL_CODE==0x8085) || (VI_ATTR_MODEL_CODE==0x8087) || (VI_ATTR_MODEL_CODE==0x8089))}"
    rm = ResourceManager()
    try:
        raw_spec_list = rm.list_resources(search_string)
    except:
        return paramsets

    for spec in raw_spec_list:
        _, _, model, serial, _ = spec.split('::', 4)
        model = SpecTypes(int(model, 0))
        paramsets.append(ParamSet(CCS, usb=spec, serial=serial, model=model))
    return paramsets


class ThorlabsCCSError(Error):
    pass


class NiceCCSLib(NiceLib):
    """ Provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.TCube.DCServo.dll"""
    _info = load_lib('tlccs', __package__)
    _struct_maker = None
    _prefix = ('tlccs_')
    _buflen = 256
    _ret = 'error_code'

    def _ret_error_code(error_code, niceobj):
        if error_code != 0:
            if niceobj is None:
                raise ThorlabsCCSError(NiceCCSLib.error_message(0, error_code)[0])
            else:
                raise ThorlabsCCSError(niceobj.error_message(error_code)[0])

    init = ('in', 'in', 'in', 'out')
    error_message = ('in', 'in', 'buf[512]')

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
        'error_message': ('in', 'in', 'buf[512]', {'ret': 'ignore'})
    })


class SpecTypes(Enum):
    CCS100 = NiceCCSLib.CCS100_PID
    CCS125 = NiceCCSLib.CCS125_PID
    CCS150 = NiceCCSLib.CCS150_PID
    CCS175 = NiceCCSLib.CCS175_PID
    CCS200 = NiceCCSLib.CCS200_PID

class Calibration(Enum):
    Factory = 0
    User = 1

class CorrectionType(Enum):
    Store = 2
    OneTime = 1

class ID_Info():
    def __init__(self, manufacturer, device_name, serial_number, firmware_version,
                 driver_version):
        self.manufacturer = manufacturer
        self.device_name = device_name
        self.serial_number = serial_number
        self.firmware_version = firmware_version
        self.driver_version = driver_version

class Status():
    def __init__(self, status):
        status = status % 256
        self.waiting_for_trig = bool(status//WAITING_FOR_TRIG)

        status = status % 32
        self.data_ready = bool(status//DATA_READY)

        status = status % 8
        self.cont_scan_in_progress = bool(status//CONT_SCAN)

        status = status % 4
        self.idle = bool(status//IDLE)
        return


class CCS(Spectrometer):
    """
    A CCS-series Thorlabs spectrometer.

    If this construcor is called, it will
    connect to the first available spectrometer (if there is at least one).
    It can also be accessed by calling get_spectrometer using any one of the
    parameters 'address', 'serial', or 'model'.  Calling the function
    :py:func:`~instrumental.drivers.instrument`, using any one of
    the parameters 'ccs_usb_address', 'ccs_serial_number', or 'ccs_model'
    will also return a CCS instance (if successful).
    """
    def _initialize(self):
        self.Status = Status
        self.ID_Info = ID_Info
        self.CorrectionType = CorrectionType
        self.Calibration = Calibration
        self.SpecTypes = SpecTypes
        self._address = self._paramset['usb']
        self._serial_number = self._paramset['serial']
        self._model = self._paramset['model']
        self._background = np.zeros((NUM_RAW_PIXELS, 1))
        self._NiceCCSLib = NiceCCSLib
        self._open(self._address)
        self._wavelength_array = self.calibrate_wavelength(calibration_type=Calibration.Factory)

    def __del__(self):
        self.close()

    def _open(self, address, id_query=True, reset=False):
        """Initialize a CCS spectrometer connected at the provided address.

        Parameters
        ----------
        id_query : bool, optional
            This parameter specifies whether an identification query is
            performed during the initialization process.
        resetDevice : bool, optional
            This parameter specifies whether the instrument is reset during the
            initialization process.
        """
        handle = self._NiceCCSLib.init(self._address, True, False)
        self._NiceCCS = self._NiceCCSLib.NiceCCS(handle)

    def close(self):
        """Close the spectrometer"""
        self._NiceCCS.close()

    def get_integration_time(self):
        """ Returns the integration time."""
        int_time = self._NiceCCS.getIntegrationTime()
        return Q_(int_time, 's')

    @check_units(integration_time = 's')
    def set_integration_time(self, integration_time, stop_scan=True):
        """ Sets the integration time."""
        if stop_scan:
            self.stop_scan()
        self._NiceCCS.setIntegrationTime(integration_time.to('s').magnitude)
        return

    def start_single_scan(self):
        self._NiceCCS.startScan()

    def start_continuous_scan(self):
        self._NiceCCS.startScanCont()

    def start_scan_trg(self):
        """Arms spectrometer to wait for a signal from the external trigger
        before executing scan.

        Note that the function returns immediately, and does not wait for the
        trigger or for the scan to finish.

        Note also that this cancels other scans in progress.
        """
        self._NiceCCS.startScanExtTrig()

    def start_cont_scan_trg(self):
        """Arms spectrometer for continuous external triggering.

        The spectrometer will wait for a signal from the external trigger before
        executing a  scan, will rearm immediatley after that scan has completed,
        and so on.

        Note that the function returns immediately, and does not wait for the
        trigger or for the scan to finish.

        Note also that this cancels other scans in progress.
        """
        self._NiceCCS.startScanContExtTrig()

    def stop_scan(self):
        # This is hacky but they do not provide a good function to stop a scan.
        integration_time = self.get_integration_time()
        self.set_integration_time('1ms', False)
        self.start_single_scan()
        time.sleep(0.001)
        self.set_integration_time(integration_time, False)

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
        status = self._NiceCCS.getDeviceStatus()
        return Status(status)

    def is_data_ready(self):
        """Indicates if the spectrometer has data ready to transmit. """
        status = self.get_status()
        return status.data_ready

    def is_idle(self):
        """
        Supposedly returns 'True' if the spectrometer is idle.

        The status bit on the spectrometer this driver was tested with
        did not seem to work properly.  This may or may not be a genereal issue.
        """
        status = self.get_status()
        return status.idle

    def waiting_for_trig(self):
        """
        Indicates if the spectrometer is waiting for an external trigger signal.
        """
        status = self.get_status()
        return status.waiting_for_trig

    def cont_scan_in_progress(self):
        """
        Indicates if a continuous scan is in progress
        """
        status = self.get_status()
        return status.cont_scan_in_progress

    def get_scan_data(self):
        """Returns the processed scan data.

        Contains the pixel values from the last completed scan.

        Returns
        -------
        data : numpy array of type float with of length NUM_RAW_PIXELS = 3648,
        """
        data = self._NiceCCS.getScanData()
        return self._cdata_to_numpy(data)

    def _cdata_to_numpy(self, cdata, data_type=float, size=None):
        if size is None:
            size = self._NiceCCSLib.TLCCS_NUM_PIXELS*BYTES_PER_DOUBLE
        buf = buffer(ffi.buffer(ffi.addressof(cdata), size)[:])
        return np.frombuffer(buf, data_type)

    def _get_raw_scan_data(self):
        """Reads out the raw scan data.

        No amplitude correction is applied."""
        data = self._NiceCCS.getRawScanData()
        return self._cdata_to_numpy(data)

    def reset(self):
        """ Resets the device."""
        self._NiceCCS.reset()

    def stop_and_clear(self):
        """ Stops any scans in progress, and clears any data waiting to transmit."""
        self.stop_scan()
        while self.is_data_ready():
            self.get_scan_data()

    def take_data(self, integration_time=None, num_avg=1, use_background=False):
        """Returns scan data.

        The data can be averaged over a number of trials 'num_Avg' if desired.
        The stored backgorund spectra can also be subtracted from the data.

        Parameters
        ----------
        integration_time : float, optional
            The integration time in seconds.
            If not specified, the current integration time is used.

            Note that in practice, times greater than 50 seconds do
            not seem to work properly.
        num_avg : int, Default=1
            The number of spectra to average over.
        use_background : bool, Default=False
            If true, the spectrometer subtracts the current background spectra
            (stored in self._background) from the data.

        Returns
        -------
        data : numpy array of float of size (self.num_pixels, 1)
            The amplitude data from the spectrometer, given in arbitrary units.
        wavelength_data : numpy array of float of size (self.numpixel, 1)
            The wavelength (in nm) corresponding to each pixel.
        """
        self.stop_and_clear()
        if integration_time is not None:
            self.set_integration_time(integration_time)
        else:
            integration_time = self.get_integration_time()
        integration_time = Q_(integration_time)
        wait_time = integration_time/100.

        self.start_continuous_scan()

        for i in range(num_avg):
            time.sleep(integration_time.to('s').magnitude)
            while not self.is_data_ready():
                time.sleep(wait_time.to('s').magnitude)
            temp = self.get_scan_data()
            if i == 0:
                data = temp
            else:
                data = data + temp
            if sum(temp >= (1.0 - 1e-5)):
                raise Warning('Raw data is saturated')

        self.stop_and_clear()
        data = data/num_avg
        if use_background:
            data = data-self._background
        return [data, self._wavelength_array]

    def set_background(self, integration_time=None, num_avg=1):
        """Collects a background spectrum using the given settings.

        Both the integration time and the number of spectra to average over can
        be specified as paramters.
        The background spectra itself is returned.

        Parameters
        ----------
        integration_time : float
            The integration time, in second.  If None,the current integration is used.
        num_avg : int
            The number of spectra to average over. The default is 1 (no averaging).
        """
        self._background, _ = self.take_data(integration_time, num_avg)
        return self._background

    @check_enums(calibration_type = Calibration)
    def calibrate_wavelength(self, calibration_type=Calibration.User,
                             wavelength_array=None, pixel_array=None):
        """Sets a custom pixel-wavelength calibration.

        The wavelength and pixel points are used to interpolate the correlation between pixel
        and wavelength.

        Note that the given values must be strictly increasing as a function of
        wavelength, and that the lenght of the arrays must be equal and be
        between 4 and 10 (inclusive).  Note that there are also some other
        requirements, that seem to have something with the calibration data points
        being somewhat'smooth' that are not specified in the documentation and
        may result in the not very descriptive 'Invalid user wavelength
        adjustment data' error.

        If calibration_type is Calibration.User, then the last 3 arguments must
        be given, and are used to set the wavelength calibration.

        If calibration_type is Calibration.Factory, then the last three arguments
        are ignored, and the default factory wavelength calibration is used.

        Parameters
        ----------
        pixel_data : array of int
            The pixel indices for the interpolation.
        wavelength_data : array of float
            The wavelengths (in nm) to be used in the interpolation.
        calibration_type : Calibration
        """
        if calibration_type == Calibration.User:
            num_points = len(pixel_array)
            print(num_points)
            if len(wavelength_array) != num_points:
                raise ValueError("The wavelength and pixel arrays passed to calibrate_wavelength must be of the same length")
            if wavelength_array is None or pixel_array is None:
                raise ValueError("wavelength_array and pixel_array must be passed to calibrate_wavelength if calibration_type is Calibration.User")
            self._NiceCCS.setWavelengthData(pixel_array, wavelength_array, num_points)
        wavelength_array, _, _ = self._NiceCCS.getWavelengthData(calibration_type.value)
        self._wavelength_array = self._cdata_to_numpy(wavelength_array)
        return self._wavelength_array

    @check_enums(mode=CorrectionType)
    def set_amplitude_data(self, correction_factors, start_index=0, mode=CorrectionType.Store):
        """Sets the amplitude correction factors.

        These factors multiply the pixels intensities to correct for variations
        between pixels.

        On start-up, these are all set to unity.  The factors are set by the values in
        correction_factors, starting with pixel start_index.

        Parameters
        ---------
        correction_factors : array of float
            Correction factors for the pixels.
        num_points : int
            The number of pixels to apply the correction factors (typically the
            length of correction_factors).
        start_index : int
            The index of the first pixel to which the correction factors
            will be applied.
        mode : CorrectionType
            Can be either 'store' or 'one_time'.  If set to
            OneTime, the correction factors are only applied to the current
            data.  If set to Store, the correction factors will be applied to
            the current data and all future data.
        """
        num_points = len(correction_factors)
        if (num_points + start_index) > NUM_RAW_PIXELS:
            raise ValueError('Invalid combination of start_index and num_points in set_amplitude_data')
        self._NiceCCS.setAmplitudeData(correction_factors, num_points,
                                       start_index, mode.value)

    def get_amplitude_data(self, mode=CorrectionType.Store):
        """Gets the amplitude correction factors.

        Parameters
        ---------
        mode : str
            This parameter can be either 'stored' or 'one_time'.  If set to
            'one_time', the correction factors for the current data are
            returned.  If set to 'stored', the correction factors stored in
            the spectrometers non-volatile memory will be returned.
        Returns
        -------
        correction_factors : array of float
            Array of pixel correction factors, of length NUM_RAW_PIXELS.
        """
        num_points = NUM_RAW_PIXELS
        start_index = 0
        factors = self._NiceCCS.getAmplitudeData(start_index, num_points, mode.value)
        return self._cdata_to_numpy(factors)

    def get_device_info(self):
        """Returns and instance of ID_Infor, containing various device
        information."""
        rets = self._NiceCCS.identificationQuery()
        return ID_Info(*list(rets))
