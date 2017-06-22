# -*- coding: utf-8 -*-
# Copyright 2016-2017 Nate Bogdanowicz
from __future__ import division
from past.builtins import unicode

import sys
import time
from enum import Enum
from collections import OrderedDict
import numpy as np
from nicelib import NiceLib, NiceObjectDef, load_lib

from ... import Q_, u
from ...errors import Error, InstrumentTypeError, TimeoutError
from ..util import check_units, check_enums
from .. import _ParamDict
from . import DAQ


__all__ = ['NIDAQ', 'AnalogIn', 'AnalogOut', 'VirtualDigitalChannel', 'SampleMode', 'EdgeSlope',
           'TerminalConfig', 'RelativeTo', 'ProductCategory', 'DAQError']


def to_bytes(value, codec='utf-8'):
    """Encode a unicode string as bytes or pass through an existing bytes object"""
    if isinstance(value, bytes):
        return value
    elif isinstance(value, unicode):
        value.encode(codec)
    else:
        return bytes(value)


def call_with_timeout(func, timeout):
    """Call a function repeatedly until successful or timeout elapses

    timeout : float or None
        If None, only try to call `func` once. If negative, try until successful. If nonnegative,
        try for up to `timeout` seconds. If a non-None timeout is given, hides any exceptions that
        `func` causes. If timeout elapses, raises a TimeoutError.
    """
    if timeout is None:
        return func()

    cur_time = start_time = time.time()
    max_time = start_time + float(timeout)
    while cur_time <= max_time:
        try:
            return func()
        except:
            pass
        cur_time = time.time()

    raise TimeoutError


def _instrument(params):
    if 'nidaq_devname' not in params:
        raise InstrumentTypeError("NIDAQ requires 'nidaq_devname'")
    dev_name = params['nidaq_devname']
    return NIDAQ(dev_name)


def list_instruments():
    dev_names = NiceNI.GetSysDevNames().decode().split(',')
    instruments = []
    for dev_name in dev_names:
        dev_name = dev_name.strip("'")
        if not dev_name:
            continue
        params = _ParamDict("<NIDAQ '{}'>".format(dev_name))
        params['module'] = 'daq.ni'
        params['nidaq_devname'] = dev_name
        instruments.append(params)
    return instruments


class DAQError(Error):
    def __init__(self, code):
        msg = "({}) {}".format(code, NiceNI.GetErrorString(code))
        self.code = code
        super(DAQError, self).__init__(msg)


class NotSupportedError(DAQError):
    pass


info = load_lib('ni', __package__)


class NiceNI(NiceLib):
    _info = info
    _prefix = ('DAQmx_', 'DAQmx')
    _buflen = 512
    _use_numpy = True

    def _ret(code):
        if code != 0:
            raise DAQError(code)

    GetErrorString = ('in', 'buf', 'len')
    GetSysDevNames = ('buf', 'len')
    CreateTask = ('in', 'out')

    Task = NiceObjectDef(doc="A Nice-wrapped NI Task", attrs={
        'StartTask': ('in'),
        'StopTask': ('in'),
        'ClearTask': ('in'),
        'WaitUntilTaskDone': ('in', 'in'),
        'IsTaskDone': ('in', 'out'),
        'TaskControl': ('in', 'in'),
        'CreateAIVoltageChan': ('in', 'in', 'in', 'in', 'in', 'in', 'in', 'in'),
        'CreateAOVoltageChan': ('in', 'in', 'in', 'in', 'in', 'in', 'in'),
        'CreateDIChan': ('in', 'in', 'in', 'in'),
        'CreateDOChan': ('in', 'in', 'in', 'in'),
        'ReadAnalogF64': ('in', 'in', 'in', 'in', 'arr', 'len=in', 'out', 'ignore'),
        'ReadAnalogScalarF64': ('in', 'in', 'out', 'ignore'),
        'ReadDigitalScalarU32': ('in', 'in', 'out', 'ignore'),
        'WriteAnalogF64': ('in', 'in', 'in', 'in', 'in', 'in', 'out', 'ignore'),
        'WriteAnalogScalarF64': ('in', 'in', 'in', 'in', 'ignore'),
        'WriteDigitalScalarU32': ('in', 'in', 'in', 'in', 'ignore'),
        'GetBufInputBufSize': ('in', 'out'),
        'GetBufInputOnbrdBufSize': ('in', 'out'),
        'CfgSampClkTiming': ('in', 'in', 'in', 'in', 'in', 'in'),
        'CfgImplicitTiming': ('in', 'in', 'in'),
        'CfgOutputBuffer': ('in', 'in'),
        'CfgDigEdgeStartTrig': ('in', 'in', 'in'),
        'SetReadOffset': ('in', 'in'),
        'GetReadOffset': ('in', 'out'),
        'SetReadRelativeTo': ('in', 'in'),
        'GetReadRelativeTo': ('in', 'out'),
        'SetReadOverWrite': ('in', 'in'),
        'GetReadOverWrite': ('in', 'out'),
    })

    Device = NiceObjectDef({
        # Device properties
        'GetDevIsSimulated': ('in', 'out'),
        'GetDevProductCategory': ('in', 'out'),
        'GetDevProductType': ('in', 'buf', 'len'),
        'GetDevProductNum': ('in', 'out'),
        'GetDevSerialNum': ('in', 'out'),
        'GetDevAccessoryProductTypes': ('in', 'buf', 'len=20'),
        'GetDevAccessoryProductNums': ('in', 'arr', 'len=20'),
        'GetDevAccessorySerialNums': ('in', 'arr', 'len=20'),
        'GetCarrierSerialNum': ('in', 'out'),
        'GetDevChassisModuleDevNames': ('in', 'buf', 'len'),
        'GetDevAnlgTrigSupported': ('in', 'out'),
        'GetDevDigTrigSupported': ('in', 'out'),

        # AI Properties
        'GetDevAIPhysicalChans': ('in', 'buf', 'len'),
        'GetDevAISupportedMeasTypes': ('in', 'arr', 'len=32'),
        'GetDevAIMaxSingleChanRate': ('in', 'out'),
        'GetDevAIMaxMultiChanRate': ('in', 'out'),
        'GetDevAIMinRate': ('in', 'out'),
        'GetDevAISimultaneousSamplingSupported': ('in', 'out'),
        'GetDevAISampModes': ('in', 'arr', 'len=3'),
        'GetDevAITrigUsage': ('in', 'out'),
        'GetDevAIVoltageRngs': ('in', 'arr', 'len=32'),
        'GetDevAIVoltageIntExcitDiscreteVals': ('in', 'arr', 'len=32'),
        'GetDevAIVoltageIntExcitRangeVals': ('in', 'arr', 'len=32'),
        'GetDevAICurrentRngs': ('in', 'arr', 'len=32'),
        'GetDevAICurrentIntExcitDiscreteVals': ('in', 'arr', 'len=32'),
        'GetDevAIBridgeRngs': ('in', 'arr', 'len=32'),
        'GetDevAIResistanceRngs': ('in', 'arr', 'len=32'),
        'GetDevAIFreqRngs': ('in', 'arr', 'len=32'),
        'GetDevAIGains': ('in', 'arr', 'len=32'),
        'GetDevAICouplings': ('in', 'out'),
        'GetDevAILowpassCutoffFreqDiscreteVals': ('in', 'arr', 'len=32'),
        'GetDevAILowpassCutoffFreqRangeVals': ('in', 'arr', 'len=32'),
        'GetAIDigFltrTypes': ('in', 'arr', 'len=5'),
        'GetDevAIDigFltrLowpassCutoffFreqDiscreteVals': ('in', 'arr', 'len=32'),
        'GetDevAIDigFltrLowpassCutoffFreqRangeVals': ('in', 'arr', 'len=32'),

        # AO Properties
        'GetDevAOPhysicalChans': ('in', 'buf', 'len'),
        'GetDevAOSupportedOutputTypes': ('in', 'arr', 'len=3'),
        'GetDevAOSampClkSupported': ('in', 'out'),
        'GetDevAOSampModes': ('in', 'arr', 'len=3'),
        'GetDevAOMaxRate': ('in', 'out'),
        'GetDevAOMinRate': ('in', 'out'),
        'GetDevAOTrigUsage': ('in', 'out'),
        'GetDevAOVoltageRngs': ('in', 'arr', 'len=32'),
        'GetDevAOCurrentRngs': ('in', 'arr', 'len=32'),
        'GetDevAOGains': ('in', 'arr', 'len=32'),

        # DI Properties
        'GetDevDILines': ('in', 'buf', 'len'),
        'GetDevDIPorts': ('in', 'buf', 'len'),
        'GetDevDIMaxRate': ('in', 'out'),
        'GetDevDITrigUsage': ('in', 'out'),

        # DO Properties
        'GetDevDOLines': ('in', 'buf', 'len'),
        'GetDevDOPorts': ('in', 'buf', 'len'),
        'GetDevDOMaxRate': ('in', 'out'),
        'GetDevDOTrigUsage': ('in', 'out'),

        # CI Properties
        'GetDevCIPhysicalChans': ('in', 'buf', 'len'),
        'GetDevCISupportedMeasTypes': ('in', 'arr', 'len=15'),
        'GetDevCITrigUsage': ('in', 'out'),
        'GetDevCISampClkSupported': ('in', 'out'),
        'GetDevCISampModes': ('in', 'arr', 'len=3'),
        'GetDevCIMaxSize': ('in', 'out'),
        'GetDevCIMaxTimebase': ('in', 'out'),

        # CO Properties
        'GetDevCOPhysicalChans': ('in', 'buf', 'len'),
        'GetDevCOSupportedOutputTypes': ('in', 'arr', 'len=3'),
        'GetDevCOSampClkSupported': ('in', 'out'),
        'GetDevCOSampModes': ('in', 'arr', 'len=3'),
        'GetDevCOTrigUsage': ('in', 'out'),
        'GetDevCOMaxSize': ('in', 'out'),
        'GetDevCOMaxTimebase': ('in', 'out'),

        # Other Device Properties
        'GetDevTEDSHWTEDSSupported': ('in', 'out'),
        'GetDevNumDMAChans': ('in', 'out'),
        'GetDevBusType': ('in', 'out'),
        'GetDevPCIBusNum': ('in', 'out'),
        'GetDevPCIDevNum': ('in', 'out'),
        'GetDevPXIChassisNum': ('in', 'out'),
        'GetDevPXISlotNum': ('in', 'out'),
        'GetDevCompactDAQChassisDevName': ('in', 'buf', 'len'),
        'GetDevCompactDAQSlotNum': ('in', 'out'),
        'GetDevTCPIPHostname': ('in', 'buf', 'len'),
        'GetDevTCPIPEthernetIP': ('in', 'buf', 'len'),
        'GetDevTCPIPWirelessIP': ('in', 'buf', 'len'),
        'GetDevTerminals': ('in', 'buf', 'len=2048'),
    })

    #Device = NiceObjectDef({
    #    'GetDevProductType': ('in', 'buf', 'len'),
    #    'GetDev(AI|AO|CI|CO)PhysicalChans': ('in', 'buf', 'len'),
    #    'GetDevAIVoltageRngs': ('in', 'arr20', 'len'),
    #    'GetDevProductCategory': ('in', 'out'),
    #})

ffi = NiceNI._info._ffi


if 'sphinx' in sys.modules:
    # Use mock class to allow sphinx to import this module
    class Values(object):
        def __getattr__(self, name):
            return name
else:
    class Values(object):
        pass

Val = Values()
for name, attr in NiceNI.__dict__.items():
    if name.startswith('Val_'):
        setattr(Val, name[4:], attr)


class SampleMode(Enum):
    finite = Val.FiniteSamps
    continuous = Val.ContSamps
    hwtimed = Val.HWTimedSinglePoint


class EdgeSlope(Enum):
    rising = Val.RisingSlope
    falling = Val.FallingSlope


class TerminalConfig(Enum):
    default = Val.Cfg_Default
    RSE = Val.RSE
    NRSE = Val.NRSE
    diff = Val.Diff
    pseudo_diff = Val.PseudoDiff


class RelativeTo(Enum):
    FirstSample = Val.FirstSample
    CurrReadPos = Val.CurrReadPos
    RefTrig = Val.RefTrig
    FirstPretrigSamp = Val.FirstPretrigSamp
    MostRecentSamp = Val.MostRecentSamp


class ProductCategory(Enum):
    MSeriesDAQ = Val.MSeriesDAQ
    XSeriesDAQ = Val.XSeriesDAQ
    ESeriesDAQ = Val.ESeriesDAQ
    SSeriesDAQ = Val.SSeriesDAQ
    BSeriesDAQ = Val.BSeriesDAQ
    SCSeriesDAQ = Val.SCSeriesDAQ
    USBDAQ = Val.USBDAQ
    AOSeries = Val.AOSeries
    DigitalIO = Val.DigitalIO
    TIOSeries = Val.TIOSeries
    DynamicSignalAcquisition = Val.DynamicSignalAcquisition
    Switches = Val.Switches
    CompactDAQChassis = Val.CompactDAQChassis
    CSeriesModule = Val.CSeriesModule
    SCXIModule = Val.SCXIModule
    SCCConnectorBlock = Val.SCCConnectorBlock
    SCCModule = Val.SCCModule
    NIELVIS = Val.NIELVIS
    NetworkDAQ = Val.NetworkDAQ
    SCExpress = Val.SCExpress
    Unknown = Val.Unknown


# Manually taken from NI's support docs since there doesn't seem to be a DAQmx function to do
# this... This list should include all possible internal channels for each type of device, and some
# of these channels will not exist on a given device.
_internal_channels = {
    ProductCategory.MSeriesDAQ:
        ['_aignd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd', '_ao2_vs_aognd', '_ao3_vs_aognd',
         '_calref_vs_aignd', '_aignd_vs_aisense', '_aignd_vs_aisense2', '_calSrcHi_vs_aignd',
         '_calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi',
         '_calSrcMid_vs_aignd', '_calSrcLo_vs_aignd', '_ai0_vs_calSrcHi', '_ai8_vs_calSrcHi',
         '_boardTempSensor_vs_aignd', '_PXI_SCXIbackplane_vs_aignd'],
    ProductCategory.XSeriesDAQ:
        ['_aignd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd', '_ao2_vs_aognd', '_ao3_vs_aognd',
         '_calref_vs_aignd', '_aignd_vs_aisense', '_aignd_vs_aisense2', '_calSrcHi_vs_aignd',
         '_calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi',
         '_calSrcMid_vs_aignd', '_calSrcLo_vs_aignd', '_ai0_vs_calSrcHi', '_ai8_vs_calSrcHi',
         '_boardTempSensor_vs_aignd'],
    ProductCategory.ESeriesDAQ:
        ['_aognd_vs_aognd', '_aognd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd',
         '_calref_vs_calref', '_calref_vs_aignd', '_ao0_vs_calref', '_ao1_vs_calref',
         '_ao1_vs_ao0', '_boardTempSensor_vs_aignd', '_aignd_vs_aignd', '_caldac_vs_aignd',
         '_caldac_vs_calref', '_PXI_SCXIbackplane_vs_aignd'],
    ProductCategory.SSeriesDAQ:
        ['_external_channel', '_aignd_vs_aignd', '_aognd_vs_aognd', '_aognd_vs_aignd',
         '_ao0_vs_aognd', '_ao1_vs_aognd', '_calref_vs_calref', '_calref_vs_aignd',
         '_ao0_vs_calref', '_ao1_vs_calref', '_calSrcHi_vs_aignd', '_calref_vs_calSrcHi',
         '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi', '_calSrcMid_vs_aignd',
         '_calSrcMid_vs_calSrcHi'],
    ProductCategory.SCSeriesDAQ:
        ['_external_channel', '_aignd_vs_aignd', '_calref_vs_aignd', '_calSrcHi_vs_aignd',
         '_aignd_vs_calSrcHi', '_calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi',
         '_aipos_vs_calSrcHi', '_aineg_vs_calSrcHi', '_cjtemp0', '_cjtemp1', '_cjtemp2',
         '_cjtemp3', '_cjtemp4', '_cjtemp5', '_cjtemp6', '_cjtemp7', '_aignd_vs_aignd0',
         '_aignd_vs_aignd1'],
    ProductCategory.USBDAQ:
        ['_cjtemp', '_cjtemp0', '_cjtemp1', '_cjtemp2', '_cjtemp3'],
    ProductCategory.DynamicSignalAcquisition:
        ['_external_channel', '_5Vref_vs_aignd', '_ao0_vs_ao0neg', '_ao1_vs_ao1neg',
         '_aignd_vs_aignd', '_ref_sqwv_vs_aignd'],
    ProductCategory.CSeriesModule:
        ['_aignd_vs_aignd', '_calref_vs_aignd', '_cjtemp', '_cjtemp0', '_cjtemp1', '_cjtemp2',
         '_aignd_vs_aisense', 'calSrcHi_vs_aignd', 'calref_vs_calSrcHi', '_calSrcHi_vs_calSrcHi',
         '_aignd_vs_calSrcHi', '_calSrcMid_vs_aignd', '_boardTempSensor_vs_aignd',
         '_ao0_vs_calSrcHi', '_ai8_vs_calSrcHi', '_cjtemp3', '_ctr0', '_ctr1', '_freqout', '_ctr2',
         '_ctr3'],
    ProductCategory.SCXIModule:
        ['_cjTemp', '_cjTemp0', '_cjTemp1', '_cjTemp2', '_cjTemp3', '_cjTemp4', '_cjTemp5',
         '_cjTemp6', '_cjTemp7', '_pPos0', '_pPos1', '_pPos2', '_pPos3', '_pPos4', '_pPos5',
         '_pPos6', '_pPos7', '_pNeg0', '_pNeg1', '_pNeg2', '_pNeg3', '_pNeg4', '_pNeg5',
         '_pNeg6', '_pNeg7', '_Vex0', '_Vex1', '_Vex2', '_Vex3', '_Vex4', '_Vex5', '_Vex6',
         '_Vex7', '_Vex8', '_Vex9', '_Vex10', '_Vex11', '_Vex12', '_Vex13', '_Vex14', '_Vex15',
         '_Vex16', '_Vex17', '_Vex18', '_Vex19', '_Vex20', '_Vex21', '_Vex22', '_Vex23',
         '_IexNeg0', '_IexNeg1', '_IexNeg2', '_IexNeg3', '_IexNeg4', '_IexNeg5', '_IexNeg6',
         '_IexNeg7', '_IexNeg8', '_IexNeg9', '_IexNeg10', '_IexNeg11', '_IexNeg12', '_IexNeg13',
         '_IexNeg14', '_IexNeg15', '_IexNeg16', '_IexNeg17', '_IexNeg18', '_IexNeg19', '_IexNeg20',
         '_IexNeg21', '_IexNeg22', '_IexNeg23', '_IexPos0', '_IexPos1', '_IexPos2', '_IexPos3',
         '_IexPos4', '_IexPos5', '_IexPos6', '_IexPos7', '_IexPos8', '_IexPos9', '_IexPos10',
         '_IexPos11', '_IexPos12', '_IexPos13', '_IexPos14', '_IexPos15', '_IexPos16', '_IexPos17',
         '_IexPos18', '_IexPos19', '_IexPos20', '_IexPos21', '_IexPos22', '_IexPos23'],
    ProductCategory.NIELVIS:
        ['_aignd_vs_aignd', '_ao0_vs_aognd', '_ao1_vs_aognd', '_calref_vs_aignd',
         '_aignd_vs_aisense', '_aignd_vs_aisense2', '_calSrcHi_vs_aignd', '_calref_vs_calSrcHi',
         '_calSrcHi_vs_calSrcHi', '_aignd_vs_calSrcHi', '_calSrcMid_vs_aignd',
         '_calSrcLo_vs_aignd', '_ai0_vs_calSrcHi', '_ai8_vs_calSrcHi', '_boardTempSensor_vs_aignd',
         '_ai16', '_ai17', '_ai18', '_ai19', '_ai20', '_ai21', '_ai22', '_ai23', '_ai24', '_ai25',
         '_ai26', '_ai27', '_ai28', '_ai29', '_ai30', '_ai31', '_vpsPosCurrent', '_vpsNegCurrent',
         '_vpsPos_vs_gnd', '_vpsNeg_vs_gnd', '_dutNeg', '_base', '_dutPos', '_fgenImpedance',
         '_ao0Impedance'],
}


@check_units(duration='?s', fsamp='?Hz')
def handle_timing_params(duration, fsamp, n_samples):
    if duration is not None:
        if fsamp is not None:
            n_samples = int((duration * fsamp).to(''))  # Exclude endpoint
        elif n_samples is not None:
            if n_samples <= 0:
                raise ValueError("`n_samples` must be greater than zero")
            fsamp = (n_samples - 1) / duration
    return fsamp, n_samples


def num_not_none(*args):
    return sum(int(arg is not None) for arg in args)


class Task(object):
    """
    Note that true DAQmx tasks can only include one type of channel (e.g. AI).
    To run multiple synchronized reads/writes, we need to make one MiniTask for
    each type, then use the same sample clock for each.
    """
    def __init__(self, *args):
        """Creates a task that uses the given channels.

        Each arg can either be a Channel or a tuple of (Channel, name_str)
        """
        self._trig_set_up = False
        self.fsamp = None
        self.n_samples = 1
        self.is_scalar = True

        self.channels = OrderedDict()
        self._mtasks = {}
        self.AOs, self.AIs, self.DOs, self.DIs, self.COs, self.CIs = [], [], [], [], [], []
        TYPED_CHANNELS = {'AO': self.AOs, 'AI': self.AIs, 'DO': self.DOs,
                          'DI': self.DIs, 'CO': self.COs, 'CI': self.CIs}
        for arg in args:
            if isinstance(arg, Channel):
                channel = arg
                name = channel.name
            else:
                channel, name = arg

            if name in self.channels:
                raise Exception("Duplicate channel name {}".format(name))

            if channel.type not in self._mtasks:
                self._mtasks[channel.type] = MiniTask(channel.daq)

            self.channels[name] = channel
            channel._add_to_minitask(self._mtasks[channel.type])

            TYPED_CHANNELS[channel.type].append(channel)
        self._setup_master_channel()

    def _setup_master_channel(self):
        master_clock = ''
        self.master_trig = ''
        self.master_type = None
        for ch_type in ['AI', 'AO', 'DI', 'DO']:
            if ch_type in self._mtasks:
                devname = ''
                for ch in self.channels.values():
                    if ch.type == ch_type:
                        devname = ch.daq.name
                        break
                master_clock = '/{}/{}/SampleClock'.format(devname, ch_type.lower())
                self.master_trig = '/{}/{}/StartTrigger'.format(devname, ch_type.lower())
                self.master_type = ch_type
                break

    @check_enums(mode=SampleMode, edge=EdgeSlope)
    @check_units(duration='?s', fsamp='?Hz')
    def set_timing(self, duration=None, fsamp=None, n_samples=None, mode='finite', edge='rising',
                   clock=''):
        self.edge = edge
        num_args_specified = num_not_none(duration, fsamp, n_samples)
        if num_args_specified == 0:
            self.n_samples = 1
        elif num_args_specified == 2:
            self.fsamp, self.n_samples = handle_timing_params(duration, fsamp, n_samples)
            for ch_type, mtask in self._mtasks.items():
                mtask.config_timing(self.fsamp, self.n_samples, mode, self.edge, '')
        else:
            raise DAQError("Must specify 0 or 2 of duration, fsamp, and n_samples")

    def _setup_triggers(self):
        for ch_type, mtask in self._mtasks.items():
            if ch_type != self.master_type:
                mtask._mx_task.CfgDigEdgeStartTrig(self.master_trig, self.edge.value)
        self._trig_set_up = True

    def run(self, write_data=None):
        """Run a task from start to finish

        Writes output data, starts the task, reads input data, stops the task, then returns the
        input data. Will wait indefinitely for the data to be received. If you need more control,
        you may instead prefer to use `write()`, `read()`, `start()`, `stop()`, etc. directly.
        """
        if not self._trig_set_up:
            self._setup_triggers()

        self.write(write_data)
        self.start()
        read_data = self.read()
        self.stop()

        return read_data

    @check_units(timeout='?s')
    def read(self, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        read_data = self._read_AI_channels(timeout_s)
        return read_data

    def write(self, write_data):
        """Write data to the output channels"""
        # Need to make sure we get data array for each output channel (AO, DO, CO...)
        for ch_name, ch in self.channels.items():
            if ch.type in ('AO', 'DO', 'CO'):
                if write_data is None:
                    raise ValueError("Must provide write_data if using output channels")
                elif ch_name not in write_data:
                    raise ValueError('write_data missing an array for output channel {}'
                                     .format(ch_name))

        # Then set up writes for each channel, don't auto-start
        self._write_AO_channels(write_data)
        # self.write_DO_channels()
        # self.write_CO_channels()

    def verify(self):
        for mtask in self._mtasks.values():
            mtask.verify()

    def reserve(self):
        for mtask in self._mtasks.values():
            mtask.reserve()

    def unreserve(self):
        for mtask in self._mtasks.values():
            mtask.unreserve()

    def abort(self):
        for mtask in self._mtasks.values():
            mtask.abort()

    def commit(self):
        for mtask in self._mtasks.values():
            mtask.commit()

    def start(self):
        for ch_type, mtask in self._mtasks.items():
            if ch_type != self.master_type:
                mtask.start()
        self._mtasks[self.master_type].start()  # Start the master last

    def stop(self):
        self._mtasks[self.master_type].stop()  # Stop the master first
        for ch_type, mtask in self._mtasks.items():
            if ch_type != self.master_type:
                mtask.stop()

    def _read_AI_channels(self, timeout_s):
        """ Returns a dict containing the AI buffers. """
        is_scalar = self.fsamp is None
        mx_task = self._mtasks['AI']._mx_task
        buf_size = self.n_samples * len(self.AIs)
        data, n_samps_read = mx_task.ReadAnalogF64(-1, timeout_s, Val.GroupByChannel, buf_size)

        res = {}
        for i, ch in enumerate(self.AIs):
            start = i * n_samps_read
            stop = (i + 1) * n_samps_read
            ch_data = data[start:stop] if not is_scalar else data[start]
            res[ch.path] = Q_(ch_data, 'V')

        if is_scalar:
            res['t'] = Q_(0., 's')
        else:
            end_t = (n_samps_read-1)/self.fsamp.m_as('Hz') if self.fsamp is not None else 0
            res['t'] = Q_(np.linspace(0., end_t, n_samps_read), 's')
        return res

    def _write_AO_channels(self, data):
        if 'AO' not in self._mtasks:
            return
        mx_task = self._mtasks['AO']._mx_task
        ao_names = [name for (name, ch) in self.channels.items() if ch.type == 'AO']
        arr = np.concatenate([Q_(data[ao]).to('V').magnitude for ao in ao_names])
        arr = arr.astype(np.float64)
        n_samps_per_chan = list(data.values())[0].magnitude.size
        mx_task.WriteAnalogF64(n_samps_per_chan, False, -1., Val.GroupByChannel, arr)


class MiniTask(object):
    def __init__(self, daq):
        self.daq = daq
        handle = NiceNI.CreateTask('')
        self._mx_task = NiceNI.Task(handle)
        self.AIs = []
        self.AOs = []
        self.chans = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        try:
            self._mx_task.StopTask()
        except:
            if value is None:
                raise  # Only raise new error from StopTask if we started with one
        finally:
            self._mx_task.ClearTask()  # Always clean up our memory

    @check_enums(mode=SampleMode, edge=EdgeSlope)
    @check_units(fsamp='Hz')
    def config_timing(self, fsamp, n_samples, mode='finite', edge='rising', clock=''):
        clock = to_bytes(clock)
        self._mx_task.CfgSampClkTiming(clock, fsamp.m_as('Hz'), edge.value, mode.value, n_samples)

        # Save for later
        self.n_samples = n_samples
        self.fsamp = fsamp

    def reserve(self):
        self._mx_task.TaskControl(Val.Task_Reserve)

    def unreserve(self):
        self._mx_task.TaskControl(Val.Task_Unreserve)

    def abort(self):
        self._mx_task.TaskControl(Val.Task_Abort)

    def reserve_with_timeout(self, timeout):
        """Try, multiple times if necessary, to reserve the hardware resources needed for the task

        If `timeout` is None, only tries once. Otherwise, tries repeatedly until successful, raising
        a TimeoutError if the given timeout elapses. To retry without limit, use a negative
        `timeout`.
        """
        call_with_timeout(self.reserve, timeout)

    def verify(self):
        self._mx_task.TaskControl(Val.Task_Verify)

    def commit(self):
        self._mx_task.TaskControl(Val.Task_Commit)

    def start(self):
        self._mx_task.StartTask()

    def stop(self):
        self._mx_task.StopTask()

    @check_enums(term_cfg=TerminalConfig)
    @check_units(vmin='?V', vmax='?V')
    def add_AI_channel(self, ai_path, term_cfg='default', vmin=None, vmax=None):
        self.AIs.append(ai_path)
        default_min, default_max = self.daq._max_AI_range()
        vmin = default_min if vmin is None else vmin
        vmax = default_max if vmax is None else vmax
        self._mx_task.CreateAIVoltageChan(ai_path, '', term_cfg.value, vmin.m_as('V'),
                                          vmax.m_as('V'), Val.Volts, '')

    def add_AO_channel(self, ao_path):
        self.AOs.append(ao_path)
        min, max = self.daq._max_AI_range()
        self._mx_task.CreateAOVoltageChan(ao_path, '', min.m_as('V'), max.m_as('V'), Val.Volts, '')

    def add_DI_channel(self, di_path):
        self._mx_task.CreateDIChan(di_path, '', Val.ChanForAllLines)

    def add_DO_channel(self, do_path):
        self.chans.append(do_path)
        self._mx_task.CreateDOChan(do_path, '', Val.ChanForAllLines)

    @check_units(timeout='?s')
    def read_AI_scalar(self, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        value = self._mx_task.ReadAnalogScalarF64(timeout_s)
        return Q_(value, 'V')

    @check_units(timeout='?s')
    def read_AI_channels(self, samples=-1, timeout=None):
        """Perform an AI read and get a dict containing the AI buffers"""
        samples = int(samples)
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))

        if samples == -1:
            buf_size = self._mx_task.GetBufInputBufSize() * len(self.AIs)
        else:
            buf_size = samples * len(self.AIs)

        data, n_samples_read = self._mx_task.ReadAnalogF64(samples, timeout_s, Val.GroupByChannel,
                                                           buf_size)
        res = {}
        for i, ch_name in enumerate(self.AIs):
            start = i * n_samples_read
            stop = (i+1) * n_samples_read
            res[ch_name] = Q_(data[start:stop], 'V')
        res['t'] = Q_(np.linspace(0, n_samples_read/self.fsamp.m_as('Hz'),
                                  n_samples_read, endpoint=False), 's')
        return res

    @check_units(value='V', timeout='?s')
    def write_AO_scalar(self, value, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        self._mx_task.WriteAnalogScalarF64(True, timeout_s, float(value.m_as('V')))

    @check_units(timeout='?s')
    def read_DI_scalar(self, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        value = self._mx_task.ReadDigitalScalarU32(timeout_s)
        return value

    @check_units(timeout='?s')
    def write_DO_scalar(self, value, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        self._mx_task.WriteDigitalScalarU32(True, timeout_s, value)

    @check_units(timeout='?s')
    def wait_until_done(self, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        self._mx_task.WAitUntilTaskDone(timeout_s)

    def overwrite(self, overwrite):
        val = Val.OverwriteUnreadSamps if overwrite else Val.DoNotOverwriteUnreadSamps
        self._mx_task.SetReadOverWrite(val)

    @check_enums(relative_to=RelativeTo)
    def relative_to(self, relative_to):
        self._mx_task.SetReadRelativeTo(relative_to.value)

    def offset(self, offset):
        self._mx_task.SetReadOffset(offset)


class Channel(object):
    pass


class AnalogIn(Channel):
    type = 'AI'

    def __init__(self, daq, chan_name):
        self.daq = daq
        self.name = chan_name
        self.path = '{}/{}'.format(daq.name, chan_name)
        self._mtask = None

    @check_enums(term_cfg=TerminalConfig)
    def _add_to_minitask(self, minitask, term_cfg='default'):
        min, max = self.daq._max_AI_range()
        mx_task = minitask._mx_task
        mx_task.CreateAIVoltageChan(self.path, '', term_cfg.value, min.m_as('V'), max.m_as('V'),
                                    Val.Volts, '')

    @check_units(duration='?s', fsamp='?Hz')
    def read(self, duration=None, fsamp=None, n_samples=None, vmin=None, vmax=None,
             reserve_timeout=None):
        """Read one or more analog input samples.

        By default, reads and returns a single sample. If two of `duration`, `fsamp`,
        and `n_samples` are given, an array of samples is read and returned.

        Parameters
        ----------
        duration : Quantity
            How long to read from the analog input, specified as a Quantity.
            Use with `fsamp` or `n_samples`.
        fsamp : Quantity
            The sample frequency, specified as a Quantity. Use with `duration`
            or `n_samples`.
        n_samples : int
            The number of samples to read. Use with `duration` or `fsamp`.

        Returns
        -------
        data : scalar or array Quantity
            The data that was read from analog input.
        """
        with self.daq._create_mini_task() as mtask:
            mtask.add_AI_channel(self.path, vmin=vmin, vmax=vmax)

            num_args_specified = num_not_none(duration, fsamp, n_samples)
            if num_args_specified == 0:
                mtask.verify()
                mtask.reserve_with_timeout(reserve_timeout)
                data = mtask.read_AI_scalar()
            elif num_args_specified == 2:
                fsamp, n_samples = handle_timing_params(duration, fsamp, n_samples)
                mtask.config_timing(fsamp, n_samples)
                mtask.verify()
                mtask.reserve_with_timeout(reserve_timeout)
                data = mtask.read_AI_channels()
            else:
                raise DAQError("Must specify 0 or 2 of duration, fsamp, and n_samples")
        return data

    def start_reading(self, fsamp=None, vmin=None, vmax=None, overwrite=False,
                      relative_to=RelativeTo.CurrReadPos, offset=0, buf_size=10):
        self._mtask = mtask = self.daq._create_mini_task()
        mtask.add_AI_channel(self.path, vmin=vmin, vmax=vmax)
        mtask.config_timing(fsamp, buf_size, mode=SampleMode.continuous)
        mtask.overwrite(overwrite)
        mtask.relative_to(relative_to)
        mtask.offset(offset)
        self._mtask.start()

    def read_sample(self, timeout=None):
        try:
            return self._mtask.read_AI_scalar(timeout)
        except DAQError as e:
            if e.code == NiceNI.ErrorSamplesNotYetAvailable:
                return None
            raise

    def stop_reading(self):
        self._mtask.stop()
        self._mtask = None


class AnalogOut(Channel):
    type = 'AO'

    def __init__(self, daq, chan_name):
        self.daq = daq
        self.name = chan_name
        self.path = '{}/{}'.format(daq.name, chan_name)

    def _add_to_minitask(self, minitask):
        min, max = self.daq._max_AO_range()
        mx_task = minitask._mx_task
        mx_task.CreateAOVoltageChan(self.path, '', min.m_as('V'), max.m_as('V'), Val.Volts, '')

    @check_units(duration='?s', fsamp='?Hz')
    def read(self, duration=None, fsamp=None, n_samples=None):
        """Read one or more analog output samples.

        Not supported by all DAQ models; requires the appropriate internal channel.

        By default, reads and returns a single sample. If two of `duration`, `fsamp`,
        and `n_samples` are given, an array of samples is read and returned.

        Parameters
        ----------
        duration : Quantity
            How long to read from the analog output, specified as a Quantity.
            Use with `fsamp` or `n_samples`.
        fsamp : Quantity
            The sample frequency, specified as a Quantity. Use with `duration`
            or `n_samples`.
        n_samples : int
            The number of samples to read. Use with `duration` or `fsamp`.

        Returns
        -------
        data : scalar or array Quantity
            The data that was read from analog output.
        """
        with self.daq._create_mini_task() as mtask:
            internal_ch_name = '{}/_{}_vs_aognd'.format(self.daq.name, self.name)
            try:
                mtask.add_AI_channel(internal_ch_name)
            except DAQError as e:
                if e.code != NiceNI.ErrorPhysicalChanDoesNotExist:
                    raise
                raise NotSupportedError("DAQ model does not have the internal channel required "
                                        "to sample the output voltage")

            num_args_specified = sum(int(arg is not None) for arg in (duration, fsamp, n_samples))

            if num_args_specified == 0:
                data = mtask.read_AI_scalar()
            elif num_args_specified == 2:
                fsamp, n_samples = handle_timing_params(duration, fsamp, n_samples)
                mtask.config_timing(fsamp, n_samples)
                data = mtask.read_AI_channels()
            else:
                raise DAQError("Must specify 0 or 2 of duration, fsamp, and n_samples")
        return data

    @check_units(duration='?s', fsamp='?Hz', freq='?Hz')
    def write(self, data, duration=None, reps=None, fsamp=None, freq=None, onboard=True):
        """Write a value or array to the analog output.

        If `data` is a scalar value, it is written to output and the function
        returns immediately. If `data` is an array of values, a buffered write
        is performed, writing each value in sequence at the rate determined by
        `duration` and `fsamp` or `freq`. You must specify either `fsamp` or
        `freq`.

        When writing an array, this function blocks until the output sequence
        has completed.

        Parameters
        ----------
        data : scalar or array Quantity
            The value or values to output, passed in Volt-compatible units.
        duration : Quantity, optional
            Used when writing arrays of data. This is how long the entirety of
            the output lasts, specified as a second-compatible Quantity. If
            `duration` is longer than a single period of data, the waveform
            will repeat. Use either this or `reps`, not both. If neither is
            given, waveform is output once.
        reps : int or float, optional
            Used when writing arrays of data. This is how many times the
            waveform is repeated. Use either this or `duration`, not both. If
            neither is given, waveform is output once.
        fsamp: Quantity, optional
            Used when writing arrays of data. This is the sample frequency,
            specified as a Hz-compatible Quantity. Use either this or `freq`,
            not both.
        freq : Quantity, optional
            Used when writing arrays of data. This is the frequency of the
            *overall waveform*, specified as a Hz-compatible Quantity. Use
            either this or `fsamp`, not both.
        onboard : bool, optional
            Use only onboard memory. Defaults to True. If False, all data will
            be continually buffered from the PC memory, even if it is only
            repeating a small number of samples many times.
        """
        if isscalar(data):
            return self._write_scalar(data)

        if num_not_none(fsamp, freq) != 1:
            raise DAQError("Need one and only one of `fsamp` or `freq`")
        if fsamp is None:
            fsamp = freq * len(data)

        if num_not_none(duration, reps) == 2:
            raise DAQError("Can use at most one of `duration` or `reps`, not both")
        if duration is None:
            duration = (reps or 1) * len(data) / fsamp

        fsamp, n_samples = handle_timing_params(duration, fsamp, len(data))

        with self.daq._create_mini_task() as mtask:
            mtask.add_AO_channel(self.path)
            mtask.set_AO_only_onboard_mem(self.path, onboard)
            mtask.config_timing(fsamp, n_samples)
            mtask.write_AO_channels({self.path: data})
            mtask.wait_until_done()

    def _write_scalar(self, value):
        with self.daq._create_mini_task() as mtask:
            mtask.add_AO_channel(self.path)
            mtask.write_AO_scalar(value)


def isscalar(value):
    if isinstance(value, Q_):
        value = value.magnitude
    return np.isscalar(value)


class Counter(Channel):
    pass


class VirtualDigitalChannel(Channel):
    type = 'DIO'

    def __init__(self, daq, line_pairs):
        self.daq = daq
        self.line_pairs = line_pairs
        self.direction = None
        self.name = self._generate_name()
        self.num_lines = len(line_pairs)
        self.ports = []
        for port_name, line_name in line_pairs:
            if port_name not in self.ports:
                self.ports.append(port_name)

    def _generate_name(self):
        """Fold up ranges. e.g. 1,2,3,4 -> 1:4"""
        port_start = None
        line_start, prev_line = None, None
        name = ''

        def get_num(name):
            return int(name[4:])

        for port, line in self.line_pairs:
            lineno = get_num(line)
            if port_start is None:
                port_start = get_num(port)
                name += '+port{}.'.format(port_start)

            if line_start is None:
                line_start = lineno
                name += str(line_start)
            elif lineno != prev_line + 1:
                # This line doesn't continue the existing range
                line_start = lineno
                if lineno != line_start:
                    name += ':{}'.format(prev_line)
                name += '+port{}.{}'.format(port_start, line_start)

            prev_line = lineno
        if lineno != line_start:
            name += ':{}'.format(prev_line)

        name = name.replace('.0:7', '')
        return name[1:]

    def _get_name(self):
        """Get DAQmx-style name of this channel"""
        return ','.join([self._get_line_path(pair) for pair in self.line_pairs])

    def _get_line_path(self, line_pair):
        return '{}/{}/{}'.format(self.daq.name, line_pair[0], line_pair[1])

    def __getitem__(self, key):
        if isinstance(key, slice):
            # Follow NI syntax convention where end of slice is included
            start = 0 if key.start is None else key.start
            stop = len(self.line_pairs) if key.stop is None else key.stop

            if start <= stop:
                stop2 = None if key.stop is None else key.stop+1
                sl = slice(key.start, stop2, 1)
            else:
                stop2 = None if stop == 0 else stop-1
                sl = slice(key.start, stop2, -1)
            pairs = self.line_pairs[sl]
        else:
            pairs = [self.line_pairs[key]]
        return VirtualDigitalChannel(self.daq, pairs)

    def __add__(self, other):
        """Concatenate two VirtualDigitalChannels"""
        if not isinstance(other, VirtualDigitalChannel):
            return NotImplemented
        line_pairs = []
        line_pairs.extend(self.line_pairs)
        line_pairs.extend(other.line_pairs)
        return VirtualDigitalChannel(self.daq, line_pairs)

    def _create_DO_int(self, value):
        """Convert nice value to that required by write_DO_scalar()"""
        out_val = 0
        for i, (port_name, line_name) in enumerate(self.line_pairs):
            line_num = int(line_name.replace('line', ''))
            bit = (value & (1 << i)) >> i
            byte = bit << line_num
            byte_num = self.ports.index(port_name)
            out_val += byte << 8*byte_num
        return out_val

    def _parse_DI_int(self, value):
        if self.num_lines == 1:
            return bool(value)
        else:
            port_bytes = {}
            for i, port_name in enumerate(self.ports):
                byte = ((0xFF << 8*i) & value) >> 8*i
                port_bytes[port_name] = byte

            out = 0
            for i, (port_name, line_name) in enumerate(self.line_pairs):
                line_num = int(line_name.replace('line', ''))
                byte = port_bytes[port_name]
                out += ((byte & (1 << line_num)) >> line_num) << i
            return out

    def read(self):
        with self.daq._create_mini_task() as t:
            t.add_DI_channel(self._get_name())
            data = t.read_DI_scalar()
        return self._parse_DI_int(data)

    def write(self, value):
        """Write a value to the digital output channel

        Parameters
        ----------
        value : int or bool
            An int representing the digital values to write. The lowest bit of
            the int is written to the first digital line, the second to the
            second, and so forth. For a single-line DO channel, can be a bool.
        """
        with self.daq._create_mini_task() as t:
            t.add_DO_channel(self._get_name())
            t.write_DO_scalar(self._create_DO_int(value))

    def write_sequence(self, data, duration=None, reps=None, fsamp=None, freq=None, onboard=True,
                       clock=''):
        """Write an array of samples to the digital output channel

        Outputs a buffered digital waveform, writing each value in sequence at
        the rate determined by `duration` and `fsamp` or `freq`. You must
        specify either `fsamp` or `freq`.

        This function blocks until the output sequence has completed.

        Parameters
        ----------
        data : array or list of ints or bools
            The sequence of samples to output. For a single-line DO channel,
            samples can be bools.
        duration : Quantity, optional
            How long the entirety of the output lasts, specified as a
            second-compatible Quantity. If `duration` is longer than a single
            period of data, the waveform will repeat. Use either this or
            `reps`, not both. If neither is given, waveform is output once.
        reps : int or float, optional
            How many times the waveform is repeated. Use either this or
            `duration`, not both. If neither is given, waveform is output once.
        fsamp: Quantity, optional
            This is the sample frequency, specified as a Hz-compatible
            Quantity. Use either this or `freq`, not both.
        freq : Quantity, optional
            This is the frequency of the *overall waveform*, specified as a
            Hz-compatible Quantity. Use either this or `fsamp`, not both.
        onboard : bool, optional
            Use only onboard memory. Defaults to True. If False, all data will
            be continually buffered from the PC memory, even if it is only
            repeating a small number of samples many times.
        """
        if (fsamp is None) == (freq is None):
            raise Exception("Need one and only one of 'fsamp' or 'freq'")
        if fsamp is None:
            fsamp = Q_(freq)*len(data)
        else:
            fsamp = Q_(fsamp)

        if (duration is not None) and (reps is not None):
            raise Exception("Can use at most one of `duration` or `reps`, not both")
        if duration is None:
            duration = (reps or 1)*len(data)/fsamp
        fsamp, n_samples = handle_timing_params(duration, fsamp, len(data))

        with self.daq._create_mini_task() as t:
            t.add_DO_channel(self._get_name())
            t.set_DO_only_onboard_mem(self._get_name(), onboard)
            t.config_timing(fsamp, n_samples, clock=clock)
            t.write_DO_channels({self.name: data}, [self])
            t.t.WaitUntilTaskDone(-1)

    def as_input(self):
        copy = VirtualDigitalChannel(self.daq, self.line_pairs)
        copy.type = 'DI'
        return copy

    def as_output(self):
        copy = VirtualDigitalChannel(self.daq, self.line_pairs)
        copy.type = 'DO'
        return copy


class NIDAQ(DAQ):
    mx = NiceNI

    def __init__(self, dev_name):
        self.name = dev_name
        self._dev = self.mx.Device(dev_name)
        self._load_analog_channels()
        self._load_internal_channels()
        self._load_digital_ports()

    def Task(self, *args):
        return Task(*args)

    def _create_mini_task(self):
        return MiniTask(self)

    def _load_analog_channels(self):
        for ai_name in self._basenames(self._dev.GetDevAIPhysicalChans()):
            setattr(self, ai_name, AnalogIn(self, ai_name))

        for ao_name in self._basenames(self._dev.GetDevAOPhysicalChans()):
            setattr(self, ao_name, AnalogOut(self, ao_name))

    def _load_internal_channels(self):
        ch_names = _internal_channels.get(self.product_category)
        for ch_name in ch_names:
            setattr(self, ch_name, AnalogIn(self, ch_name))

    def _load_digital_ports(self):
        # Need to handle general case of DI and DO ports, can't assume they're always the same...
        ports = {}
        for line_path in self._dev.GetDevDILines().decode().split(','):
            port_name, line_name = line_path.rsplit('/', 2)[-2:]
            if port_name not in ports:
                ports[port_name] = []
            ports[port_name].append(line_name)

        for port_name, line_names in ports.items():
            line_pairs = [(port_name, l) for l in line_names]
            chan = VirtualDigitalChannel(self, line_pairs)
            setattr(self, port_name, chan)

    def _AI_ranges(self):
        data = self._dev.GetDevAIVoltageRngs()
        pairs = []
        for i in range(0, len(data), 2):
            if data[i] == 0 and data[i+1] == 0:
                break
            pairs.append((data[i] * u.V, data[i+1] * u.V))
        return pairs

    def _AO_ranges(self):
        data = self._dev.GetDevAOVoltageRngs()
        pairs = []
        for i in range(0, len(data), 2):
            if data[i] == 0 and data[i+1] == 0:
                break
            pairs.append((data[i] * u.V, data[i+1] * u.V))
        return pairs

    def _max_AI_range(self):
        """The min an max voltage of the widest AI range available"""
        return max(self._AI_ranges(), key=(lambda pair: pair[1] - pair[0]))

    def _max_AO_range(self):
        """The min an max voltage of the widest AO range available"""
        return max(self._AO_ranges(), key=(lambda pair: pair[1] - pair[0]))

    @staticmethod
    def _basenames(names):
        return [path.rsplit('/', 1)[-1] for path in names.decode().split(',')]

    product_type = property(lambda self: self._dev.GetDevProductType())
    product_category = property(lambda self: ProductCategory(self._dev.GetDevProductCategory()))
    serial = property(lambda self: self._dev.GetDevSerialNum())
