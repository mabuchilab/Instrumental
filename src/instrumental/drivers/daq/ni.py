# -*- coding: utf-8 -*-
# Copyright 2016-2018 Nate Bogdanowicz
from __future__ import division
from past.builtins import unicode, basestring

import sys
import time
import weakref
from enum import Enum, EnumMeta
from collections import OrderedDict

import numpy as np
from nicelib import (NiceLib, load_lib, RetHandler,
                     Sig, NiceObject, sig_pattern)  # req: nicelib >= 0.5

from ... import Q_, u
from .. import ParamSet
from ...errors import Error, TimeoutError
from ..util import check_units, check_enums, as_enum
from ...util import to_str
from . import DAQ

__all__ = ['NIDAQ', 'AnalogIn', 'AnalogOut', 'VirtualDigitalChannel', 'SampleMode', 'EdgeSlope',
           'TerminalConfig', 'RelativeTo', 'ProductCategory', 'DAQError']


def to_bytes(value, codec='utf-8'):
    """Encode a unicode string as bytes or pass through an existing bytes object"""
    if isinstance(value, bytes):
        return value
    elif isinstance(value, unicode):
        return value.encode(codec)
    else:
        return bytes(value)


def split_list(list_bytes):
    """Split a bytestring by commas into a list of strings, stripping whitespace.

    An empty bytestring produces an empty list.
    """
    if not list_bytes:
        return []
    return [s.strip() for s in list_bytes.decode().split(',')]


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


def list_instruments():
    dev_names = split_list(NiceNI.GetSysDevNames())
    paramsets = []
    for dev_name in dev_names:
        dev_name = dev_name.strip("'")
        if not dev_name:
            continue

        paramset = ParamSet(NIDAQ,
                            name=dev_name,
                            serial=NiceNI.Device.GetDevSerialNum(dev_name),
                            model=NiceNI.Device.GetDevProductType(dev_name))
        paramsets.append(paramset)
    return paramsets


class DAQError(Error):
    def __init__(self, code):
        err_str = to_str(NiceNI.GetExtendedErrorInfo())
        msg = "({}) {}".format(code, err_str)
        self.code = code
        super(DAQError, self).__init__(msg)


class NotSupportedError(DAQError):
    pass


@RetHandler(num_retvals=0)
def ret_errcheck(code):
    if code != 0:
        raise DAQError(code)


class NiceNI(NiceLib):
    _info_ = load_lib('ni', __package__)
    _prefix_ = ('DAQmxBase_', 'DAQmxBase', 'DAQmx_', 'DAQmx')
    _buflen_ = 1024
    _use_numpy_ = True
    _ret_ = ret_errcheck

    GetErrorString = Sig('in', 'buf', 'len')
    GetSysDevNames = Sig('buf', 'len')
    GetExtendedErrorInfo = Sig('buf', 'len=2048')
    CreateTask = Sig('in', 'out')

    class Task(NiceObject):
        """A Nice-wrapped NI Task"""
        _init_ = 'CreateTask'

        StartTask = Sig('in')
        StopTask = Sig('in')
        ClearTask = Sig('in')

        WaitUntilTaskDone = Sig('in', 'in')
        IsTaskDone = Sig('in', 'out')
        TaskControl = Sig('in', 'in')
        CreateAIVoltageChan = Sig('in', 'in', 'in', 'in', 'in', 'in', 'in', 'in')
        CreateAOVoltageChan = Sig('in', 'in', 'in', 'in', 'in', 'in', 'in')
        CreateDIChan = Sig('in', 'in', 'in', 'in')
        CreateDOChan = Sig('in', 'in', 'in', 'in')
        ReadAnalogF64 = Sig('in', 'in', 'in', 'in', 'arr', 'len=in', 'out', 'ignore')
        ReadAnalogScalarF64 = Sig('in', 'in', 'out', 'ignore')
        ReadDigitalScalarU32 = Sig('in', 'in', 'out', 'ignore')
        ReadDigitalU32 = Sig('in', 'in', 'in', 'in', 'arr', 'len=in', 'out', 'ignore')
        ReadDigitalLines = Sig('in', 'in', 'in', 'in', 'arr', 'len=in', 'out', 'out', 'ignore')
        WriteAnalogF64 = Sig('in', 'in', 'in', 'in', 'in', 'in', 'out', 'ignore')
        WriteAnalogScalarF64 = Sig('in', 'in', 'in', 'in', 'ignore')
        WriteDigitalU32 = Sig('in', 'in', 'in', 'in', 'in', 'in', 'out', 'ignore')
        WriteDigitalScalarU32 = Sig('in', 'in', 'in', 'in', 'ignore')
        CfgSampClkTiming = Sig('in', 'in', 'in', 'in', 'in', 'in')
        CfgImplicitTiming = Sig('in', 'in', 'in')
        CfgOutputBuffer = Sig('in', 'in')
        CfgAnlgEdgeStartTrig = Sig('in', 'in', 'in', 'in')
        CfgDigEdgeStartTrig = Sig('in', 'in', 'in')
        CfgDigEdgeRefTrig = Sig('in', 'in', 'in', 'in')
        GetAOUseOnlyOnBrdMem = Sig('in', 'in', 'out')
        SetAOUseOnlyOnBrdMem = Sig('in', 'in', 'in')
        GetBufInputOnbrdBufSize = Sig('in', 'out')
        SetWriteRegenMode = Sig('in', 'in')

        _sigs_ = sig_pattern((
            ('Get{}', Sig('in', 'out')),
            ('Set{}', Sig('in', 'in')),
        ),(
            'SampTimingType',
            'SampQuantSampMode',
            'ReadOffset',
            'ReadRelativeTo',
            'ReadOverWrite',
            'SampQuantSampPerChan',
            'BufInputBufSize',
            'BufOutputBufSize',
            'BufOutputOnbrdBufSize',
        ))

    class Device(NiceObject):
        # Device properties
        GetDevIsSimulated = Sig('in', 'out')
        GetDevProductCategory = Sig('in', 'out')
        GetDevProductType = Sig('in', 'buf', 'len')
        GetDevProductNum = Sig('in', 'out')
        GetDevSerialNum = Sig('in', 'out')
        GetDevAccessoryProductTypes = Sig('in', 'buf', 'len=20')
        GetDevAccessoryProductNums = Sig('in', 'arr', 'len=20')
        GetDevAccessorySerialNums = Sig('in', 'arr', 'len=20')
        GetCarrierSerialNum = Sig('in', 'out')
        GetDevChassisModuleDevNames = Sig('in', 'buf', 'len')
        GetDevAnlgTrigSupported = Sig('in', 'out')
        GetDevDigTrigSupported = Sig('in', 'out')

        # AI Properties
        GetDevAIPhysicalChans = Sig('in', 'buf', 'len')
        GetDevAISupportedMeasTypes = Sig('in', 'arr', 'len=32')
        GetDevAIMaxSingleChanRate = Sig('in', 'out')
        GetDevAIMaxMultiChanRate = Sig('in', 'out')
        GetDevAIMinRate = Sig('in', 'out')
        GetDevAISimultaneousSamplingSupported = Sig('in', 'out')
        GetDevAISampModes = Sig('in', 'arr', 'len=3')
        GetDevAITrigUsage = Sig('in', 'out')
        GetDevAIVoltageRngs = Sig('in', 'arr', 'len=32')
        GetDevAIVoltageIntExcitDiscreteVals = Sig('in', 'arr', 'len=32')
        GetDevAIVoltageIntExcitRangeVals = Sig('in', 'arr', 'len=32')
        GetDevAICurrentRngs = Sig('in', 'arr', 'len=32')
        GetDevAICurrentIntExcitDiscreteVals = Sig('in', 'arr', 'len=32')
        GetDevAIBridgeRngs = Sig('in', 'arr', 'len=32')
        GetDevAIResistanceRngs = Sig('in', 'arr', 'len=32')
        GetDevAIFreqRngs = Sig('in', 'arr', 'len=32')
        GetDevAIGains = Sig('in', 'arr', 'len=32')
        GetDevAICouplings = Sig('in', 'out')
        GetDevAILowpassCutoffFreqDiscreteVals = Sig('in', 'arr', 'len=32')
        GetDevAILowpassCutoffFreqRangeVals = Sig('in', 'arr', 'len=32')
        GetAIDigFltrTypes = Sig('in', 'arr', 'len=5')
        GetDevAIDigFltrLowpassCutoffFreqDiscreteVals = Sig('in', 'arr', 'len=32')
        GetDevAIDigFltrLowpassCutoffFreqRangeVals = Sig('in', 'arr', 'len=32')

        # AO Properties
        GetDevAOPhysicalChans = Sig('in', 'buf', 'len')
        GetDevAOSupportedOutputTypes = Sig('in', 'arr', 'len=3')
        GetDevAOSampClkSupported = Sig('in', 'out')
        GetDevAOSampModes = Sig('in', 'arr', 'len=3')
        GetDevAOMaxRate = Sig('in', 'out')
        GetDevAOMinRate = Sig('in', 'out')
        GetDevAOTrigUsage = Sig('in', 'out')
        GetDevAOVoltageRngs = Sig('in', 'arr', 'len=32')
        GetDevAOCurrentRngs = Sig('in', 'arr', 'len=32')
        GetDevAOGains = Sig('in', 'arr', 'len=32')

        # DI Properties
        GetDevDILines = Sig('in', 'buf', 'len')
        GetDevDIPorts = Sig('in', 'buf', 'len')
        GetDevDIMaxRate = Sig('in', 'out')
        GetDevDITrigUsage = Sig('in', 'out')

        # DO Properties
        GetDevDOLines = Sig('in', 'buf', 'len')
        GetDevDOPorts = Sig('in', 'buf', 'len')
        GetDevDOMaxRate = Sig('in', 'out')
        GetDevDOTrigUsage = Sig('in', 'out')

        # CI Properties
        GetDevCIPhysicalChans = Sig('in', 'buf', 'len')
        GetDevCISupportedMeasTypes = Sig('in', 'arr', 'len=15')
        GetDevCITrigUsage = Sig('in', 'out')
        GetDevCISampClkSupported = Sig('in', 'out')
        GetDevCISampModes = Sig('in', 'arr', 'len=3')
        GetDevCIMaxSize = Sig('in', 'out')
        GetDevCIMaxTimebase = Sig('in', 'out')

        # CO Properties
        GetDevCOPhysicalChans = Sig('in', 'buf', 'len')
        GetDevCOSupportedOutputTypes = Sig('in', 'arr', 'len=3')
        GetDevCOSampClkSupported = Sig('in', 'out')
        GetDevCOSampModes = Sig('in', 'arr', 'len=3')
        GetDevCOTrigUsage = Sig('in', 'out')
        GetDevCOMaxSize = Sig('in', 'out')
        GetDevCOMaxTimebase = Sig('in', 'out')

        # Other Device Properties
        GetDevTEDSHWTEDSSupported = Sig('in', 'out')
        GetDevNumDMAChans = Sig('in', 'out')
        GetDevBusType = Sig('in', 'out')
        GetDevPCIBusNum = Sig('in', 'out')
        GetDevPCIDevNum = Sig('in', 'out')
        GetDevPXIChassisNum = Sig('in', 'out')
        GetDevPXISlotNum = Sig('in', 'out')
        GetDevCompactDAQChassisDevName = Sig('in', 'buf', 'len')
        GetDevCompactDAQSlotNum = Sig('in', 'out')
        GetDevTCPIPHostname = Sig('in', 'buf', 'len')
        GetDevTCPIPEthernetIP = Sig('in', 'buf', 'len')
        GetDevTCPIPWirelessIP = Sig('in', 'buf', 'len')
        GetDevTerminals = Sig('in', 'buf', 'len=2048')


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


class ValEnumMeta(EnumMeta):
    """Enum metaclass that looks up values and removes undefined members"""
    @classmethod
    def __prepare__(metacls, cls, bases, **kwds):
        return {}

    def __init__(cls, *args, **kwds):
        super(ValEnumMeta, cls).__init__(*args)

    def __new__(metacls, cls, bases, clsdict, **kwds):
        # Look up values, exclude nonexistent ones
        for name, value in list(clsdict.items()):
            try:
                clsdict[name] = getattr(Val, value)
            except AttributeError:
                del clsdict[name]

        enum_dict = super(ValEnumMeta, metacls).__prepare__(cls, bases, **kwds)
        # Must add members this way because _EnumDict.update() doesn't do everything needed
        for name, value in clsdict.items():
            enum_dict[name] = value
        return super(ValEnumMeta, metacls).__new__(metacls, cls, bases, enum_dict, **kwds)


ValEnum = ValEnumMeta('ValEnum', (Enum,), {})


class SampleMode(ValEnum):
    finite = 'FiniteSamps'
    continuous = 'ContSamps'
    hwtimed = 'HWTimedSinglePoint'


class SampleTiming(ValEnum):
    sample_clk = 'SampClk'
    burst_handshake = 'BurstHandshake'
    handshake = 'Handshake'
    on_demand = 'OnDemand'
    change_detection = 'ChangeDetection'
    pipelined_sample_clk = 'PipelinedSampClk'


class EdgeSlope(ValEnum):
    rising = 'RisingSlope'
    falling = 'FallingSlope'


class TerminalConfig(ValEnum):
    default = 'Cfg_Default'
    RSE = 'RSE'
    NRSE = 'NRSE'
    diff = 'Diff'
    pseudo_diff = 'PseudoDiff'


class RelativeTo(ValEnum):
    FirstSample = 'FirstSample'
    CurrReadPos = 'CurrReadPos'
    RefTrig = 'RefTrig'
    FirstPretrigSamp = 'FirstPretrigSamp'
    MostRecentSamp = 'MostRecentSamp'


class ProductCategory(ValEnum):
    MSeriesDAQ = 'MSeriesDAQ'
    XSeriesDAQ = 'XSeriesDAQ'
    ESeriesDAQ = 'ESeriesDAQ'
    SSeriesDAQ = 'SSeriesDAQ'
    BSeriesDAQ = 'BSeriesDAQ'
    SCSeriesDAQ = 'SCSeriesDAQ'
    USBDAQ = 'USBDAQ'
    AOSeries = 'AOSeries'
    DigitalIO = 'DigitalIO'
    TIOSeries = 'TIOSeries'
    DynamicSignalAcquisition = 'DynamicSignalAcquisition'
    Switches = 'Switches'
    CompactDAQChassis = 'CompactDAQChassis'
    CSeriesModule = 'CSeriesModule'
    SCXIModule = 'SCXIModule'
    SCCConnectorBlock = 'SCCConnectorBlock'
    SCCModule = 'SCCModule'
    NIELVIS = 'NIELVIS'
    NetworkDAQ = 'NetworkDAQ'
    SCExpress = 'SCExpress'
    Unknown = 'Unknown'


# Manually taken from NI's support docs since there doesn't seem to be a DAQmx function to do
# this... This list should include all possible internal channels for each type of device, and some
# of these channels will not exist on a given device.
# NOTE: Missing BSeriesDAQ, AOSeries, DigitalIO, TIOSeries, Switches, CompactDAQChassis,
#       SCCConnectorBlock, SCCModule, NetworkDAQ, SCExpress, and Unknown
# Also may be missing some internal channels in the given entries, so double-check this
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
    """A high-level task that can synchronize use of multiple channel types.

    Note that true DAQmx tasks can only include one type of channel (e.g. AI).
    To run multiple synchronized reads/writes, we need to make one MiniTask for
    each type, then use the same sample clock for each.
    """
    def __init__(self, *channels):
        """Create a task that uses the given channels.

        Each arg can either be a Channel or a tuple of (Channel, path_str)
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
        for arg in channels:
            if isinstance(arg, Channel):
                channel = arg
                path = channel.path
            else:
                channel, path = arg

            daq_name = channel.daq.name
            if daq_name not in self._mtasks:
                self._mtasks[daq_name] = {}

            if path in self.channels:
                raise Exception("Duplicate channel name {}".format(path))

            if channel.type not in self._mtasks[daq_name]:
                self._mtasks[daq_name][channel.type] = MiniTask(
                    channel.daq, channel.type)

            self.channels[path] = channel
            channel._add_to_minitask(self._mtasks[daq_name][channel.type])

            TYPED_CHANNELS[channel.type].append(channel)
        self._setup_master_channel()

    def _setup_master_channel(self):
        self.master_clock = ''
        self.master_trig = ''
        self.master_type = None
        # pick any device to use as master
        devname = next(iter(self._mtasks))
        for ch_type in ['AI', 'AO', 'DI', 'DO']:
            if ch_type in self._mtasks[devname]:
                self.master_clock = '/{}/{}/SampleClock'.format(
                    devname, ch_type.lower())
                self.master_trig = '/{}/{}/StartTrigger'.format(
                    devname, ch_type.lower())
                self.master_type = ch_type
                self.master_device = devname
                break

    @check_enums(mode=SampleMode, edge=EdgeSlope)
    @check_units(duration='?s', fsamp='?Hz')
    def set_timing(self, duration=None, fsamp=None, n_samples=None, mode='finite', edge='rising',
                   clock=None):
        self.edge = edge
        num_args_specified = num_not_none(duration, fsamp, n_samples)
        if num_args_specified == 0:
            self.n_samples = 1
        elif num_args_specified == 2:
            self.fsamp, self.n_samples = handle_timing_params(duration, fsamp, n_samples)
            for dev_mtasks in self._mtasks.values():
                for ch_type, mtask in dev_mtasks.items():
                    if clock is not None:
                        ch_clock = clock
                    else:
                        ch_clock = self.master_clock if ch_type != self.master_type else ''
                    mtask.config_timing(self.fsamp, self.n_samples,
                                        mode, self.edge, ch_clock)
        else:
            raise ValueError("Must specify 0 or 2 of duration, fsamp, and n_samples")

    def config_digital_edge_trigger(self, source, edge='rising', n_pretrig_samples=0):
        """Configure the task to start on a digital edge

        You must configure the task's timing using ``set_timing()`` before calling this.

        Parameters
        ----------
        source : str or Channel
            Terminal of the digital signal to use as the trigger. Note that digital channels may
            have to be given as a PFI-string, e.g. "PFI3", rather than in port-line format.
        edge : EdgeSlope or str
            Trigger slope, either 'rising' or 'falling'
        n_pretrig_samples : int
            Number of pre-trigger samples to acquire (only works for acquisition). For example, if
            you're acquiring 100 samples and `n_pretrig_samples` is 20, the data will contain 20
            samples from right before the trigger, and 80 from right after it.
        """
        # TODO: Verify that this is right for multi-tasks
        for dev_mtasks in self._mtasks.values():
            for mtask in dev_mtasks.values():
                mtask.config_digital_edge_trigger(
                    source, edge, n_pretrig_samples)

    def _setup_triggers(self):
        # TODO: Decide if/when this should ever be used. At least on M-Series DAQs, there is no need
        # to set up a digital task to trigger from an analog task, since the digital task is already
        # linked to the analog *clock*. Therefore, this is probably only useful if you want to (and
        # *can*) use separate clocks while still starting the tasks simultaneously. Maybe this is
        # *the case for simultaneous AI and AO tasks?
        for devname, dev_mtasks in self._mtasks.items():
            for ch_type, mtask in dev_mtasks.items():
                if not (ch_type == self.master_type and devname == self.master_device):
                    mtask._mx_task.CfgDigEdgeStartTrig(
                        self.master_trig, self.edge.value)
        self._trig_set_up = True

    def run(self, write_data=None):
        """Run a task from start to finish

        Writes output data, starts the task, reads input data, stops the task, then returns the
        input data. Will wait indefinitely for the data to be received. If you need more control,
        you may instead prefer to use `write()`, `read()`, `start()`, `stop()`, etc. directly.
        """
        # TODO: Decide if/when to do this. See `_setup_triggers` for more info
        #if not self._trig_set_up:
        #    self._setup_triggers()

        self.write(write_data, autostart=False)
        self.start()
        try:
            read_data = self.read()
        finally:
            self.wait_until_done()
            self.stop()

        return read_data

    @check_units(timeout='?s')
    def read(self, timeout=None):
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        read_data = self._read_AI_channels(timeout_s)
        return read_data

    def write(self, write_data, autostart=True):
        """Write data to the output channels.

        Useful when you need finer-grained control than `run()` provides.
        """
        # Need to make sure we get data array for each output channel (AO, DO, CO...)
        for ch_name, ch in self.channels.items():
            if ch.type in ('AO', 'DO', 'CO'):
                if write_data is None:
                    raise ValueError("Must provide write_data if using output channels")
                elif ch_name not in write_data:
                    raise ValueError('write_data missing an array for output channel {}'
                                     .format(ch_name))

        # Then set up writes for each channel, don't auto-start
        self._write_AO_channels(write_data, autostart=autostart)
        self._write_DO_channels(write_data, autostart=autostart)
        # self.write_CO_channels()

    def verify(self):
        """Verify the Task.

        This transitions all subtasks to the `verified` state. See the NI documentation for details
        on the Task State model.
        """
        for dev_mtasks in self._mtasks.values():
            for mtask in dev_mtasks.values():
                mtask.verify()

    def reserve(self):
        """Reserve the Task.

        This transitions all subtasks to the `reserved` state. See the NI documentation for details
        on the Task State model.
        """
        for dev_mtasks in self._mtasks.values():
            for mtask in dev_mtasks.values():
                mtask.reserve()

    def unreserve(self):
        """Unreserve the Task.

        This transitions all subtasks to the `verified` state. See the NI documentation for details
        on the Task State model.
        """
        for dev_mtasks in self._mtasks.values():
            for mtask in dev_mtasks.values():
                mtask.unreserve()

    def abort(self):
        """Abort the Task.

        This transitions all subtasks to the `verified` state. See the NI documentation for details
        on the Task State model.
        """
        for dev_mtasks in self._mtasks.values():
            for mtask in dev_mtasks.values():
                mtask.abort()

    def commit(self):
        """Commit the Task.

        This transitions all subtasks to the `committed` state. See the NI documentation for details
        on the Task State model.
        """
        for dev_mtasks in self._mtasks.values():
            for mtask in dev_mtasks.values():
                mtask.commit()

    def start(self):
        """Start the Task.

        This transitions all subtasks to the `running` state. See the NI documentation for details
        on the Task State model.
        """
        for devname, dev_mtasks in self._mtasks.items():
            for ch_type, mtask in dev_mtasks.items():
                if not (ch_type == self.master_type and devname == self.master_device):
                    mtask.start()
        # Start the master last
        self._mtasks[self.master_device][self.master_type].start()

    def stop(self):
        """Stop the Task and return it to the state it was in before it started.

        This transitions all subtasks to the state they in were before they were started, either due
        to an explicit `start()` or a call to `write()` with `autostart` set to True. See the NI
        documentation for details on the Task State model.
        """
        self._mtasks[self.master_device][self.master_type].stop(
        )  # Stop the master first
        for devname, dev_mtasks in self._mtasks.items():
            for ch_type, mtask in dev_mtasks.items():
                if not (ch_type == self.master_type and devname == self.master_device):
                    mtask.stop()

    def clear(self):
        """Clear the task and release its resources.

        This clears all subtasks and releases their resources, aborting them first if necessary.
        """
        for dev_mtasks in self._mtasks.values():
            for ch_type, mtask in dev_mtasks.items():
                mtask.clear()

    @property
    def is_done(self):
        return all(mtask.is_done for dev_mtasks in self._mtasks.values() for mtask in dev_mtasks.values())

    def wait_until_done(self, timeout=None):
        """Wait until the task is done"""
        # Only wait for one task, since they should all finish at the same time... I think
        dev_mtasks = next(iter(self._mtasks.values()))
        mtask = next(iter(dev_mtasks.values()))
        mtask.wait_until_done(timeout)

    def _read_AI_channels(self, timeout_s):
        """ Returns a dict containing the AI buffers. """
        if len(self.AIs)==0:
            return {}
        res={}
        is_scalar=self.fsamp is None
        for dev_mtasks in self._mtasks.values():
            if 'AI' not in dev_mtasks:
                continue
            mx_task = dev_mtasks['AI']._mx_task
            buf_size = self.n_samples * len(self.AIs)
            data, n_samps_read = mx_task.ReadAnalogF64(
                -1, timeout_s, Val.GroupByChannel, buf_size)

            for i, ch in enumerate(self.AIs):
                start = i * n_samps_read
                stop = (i + 1) * n_samps_read
                ch_data=data[start:stop] if not is_scalar else data[start]
                res[ch.path]=Q_(ch_data, 'V')

        if is_scalar:
            res['t'] = Q_(0., 's')
        else:
            end_t = (n_samps_read - 1) / self.fsamp.m_as('Hz') if self.fsamp is not None else 0
            res['t'] = Q_(np.linspace(0., end_t, n_samps_read), 's')
        return res

    def _write_AO_channels(self, data, autostart=True):
        if len(self.AOs) == 0:
            return {}

        for dev_name, dev_mtasks in self._mtasks.items():
            if 'AO' not in dev_mtasks:
                continue
            mx_task = dev_mtasks['AO']._mx_task

            ao_names = [name for (name, ch)
                        in self.channels.items() if ch.type == 'AO' and ch.daq.name == dev_name]
            arr = np.concatenate(
                [Q_(data[ao]).to('V').magnitude for ao in ao_names]).astype(np.float64)
            n_samps_per_chan = len(list(data.values())[0].magnitude)
            mx_task.WriteAnalogF64(
                n_samps_per_chan, autostart, -1., Val.GroupByChannel, arr)

    # TODO: need to test this
    def _write_DO_channels(self, data, autostart=True):
        if 'DO' not in self._mtasks:
            return
        for dev_name, dev_mtasks in self._mtasks.items():
            if 'DO' not in dev_mtasks:
                continue
            mx_task = dev_mtasks['DO']._mx_task
            # TODO: add check that input data is the right length
            arr = np.fromiter((ch._create_DO_int(value)
                               for (ch_name, ch) in self.channels.items() if ch.type == 'DO'
                               for value in data[ch_name]),
                              dtype='uint32')
            n_samps_per_chan = len(list(data.values())[0])
            mx_task.WriteDigitalU32(n_samps_per_chan, autostart, -1, Val.GroupByChannel, arr)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        try:
            self.stop()
        except:
            if value is None:
                raise  # Only raise new error from StopTask if we started with one
        finally:
            self.clear()  # Always clean up our memory

    def __del__(self):
        self.clear()


def mk_property(name, conv_in, conv_out, doc=None):
    getter_name = 'Get' + name
    setter_name = 'Set' + name

    def fget(mtask):
        getter = getattr(mtask._mx_task, getter_name)
        return conv_out(getter())

    def fset(mtask, value):
        setter = getattr(mtask._mx_task, setter_name)
        setter(conv_in(value))

    return property(fget, fset, doc=doc)


def enum_property(name, enum_type, doc=None):
    return mk_property(name,
                       conv_in=lambda x: as_enum(enum_type, x).value,
                       conv_out=enum_type,
                       doc=doc)


def int_property(name, doc=None):
    return mk_property(name, conv_in=int, conv_out=int, doc=doc)


class MiniTask(object):
    def __init__(self, daq, io_type):
        self.daq = daq
        self._mx_task = NiceNI.Task('')
        self.io_type = io_type
        self.chans = []
        self.fsamp = None
        self.has_trigger = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        try:
            self.stop()
        except:
            if value is None:
                raise  # Only raise new error from StopTask if we started with one
        finally:
            self.clear()  # Always clean up our memory

    sample_timing_type = enum_property('SampTimingType', SampleTiming)
    sample_mode = enum_property('SampQuantSampMode', SampleMode)
    samples_per_channel = int_property('SampQuantSampPerChan')
    input_buf_size = int_property('BufInputBufSize')
    output_buf_size = int_property('BufOutputBufSize')
    output_onboard_buf_size = int_property('BufOutputOnbrdBufSize')

    @property
    def input_onboard_buf_size(self):
        return self._mx_task.GetBufInputOnbrdBufSize()

    @check_enums(mode=SampleMode, edge=EdgeSlope)
    @check_units(fsamp='Hz')
    def config_timing(self, fsamp, n_samples, mode='finite', edge='rising', clock=''):
        clock = to_bytes(clock)
        self._mx_task.CfgSampClkTiming(clock, fsamp.m_as('Hz'), edge.value, mode.value, n_samples)

        # Save for later
        self.n_samples = n_samples
        self.fsamp = fsamp

    @check_enums(edge=EdgeSlope)
    @check_units(level='V')
    def config_analog_edge_trigger(self, source, edge='rising', level='2.5 V'):
        source_path = source if isinstance(source, basestring) else source.path
        self._mx_task.CfgAnlgEdgeStartTrig(source_path, edge.value, level.m_as('V'))

    @check_enums(edge=EdgeSlope)
    def config_digital_edge_trigger(self, source, edge='rising', n_pretrig_samples=0):
        """Configure the task to start on a digital edge

        You must configure the MiniTask's timing using ``config_timing()`` before calling this.

        Parameters
        ----------
        source : str or Channel
            Terminal of the digital signal to use as the trigger. Note that digital channels may
            have to be given as a PFI-string, e.g. "PFI3", rather than in port-line format.
        edge : EdgeSlope or str
            Trigger slope, either 'rising' or 'falling'
        n_pretrig_samples : int
            Number of pre-trigger samples to acquire (only works for acquisition). For example, if
            you're acquiring 100 samples and `n_pretrig_samples` is 20, the data will contain 20
            samples from right before the trigger, and 80 from right after it.
        """
        source_path = source if isinstance(source, basestring) else source.path
        if n_pretrig_samples > 0:
            self._mx_task.CfgDigEdgeRefTrig(source_path, edge.value, n_pretrig_samples)
        else:
            self._mx_task.CfgDigEdgeStartTrig(source_path, edge.value)
        self.has_trigger = True

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

    def clear(self):
        self._mx_task.ClearTask()

    @property
    def is_done(self):
        return bool(self._mx_task.IsTaskDone())

    def _assert_io_type(self, io_type):
        if io_type != self.io_type:
            raise TypeError("MiniTask must have io_type '{}' for this operation, but is of "
                            "type '{}'".format(io_type, self.io_type))

    @check_enums(term_cfg=TerminalConfig)
    @check_units(vmin='?V', vmax='?V')
    def add_AI_channel(self, ai, term_cfg='default', vmin=None, vmax=None):
        self._assert_io_type('AI')
        ai_path = ai if isinstance(ai, basestring) else ai.path
        self.chans.append(ai_path)
        default_min, default_max = self.daq._max_AI_range()
        vmin = default_min if vmin is None else vmin
        vmax = default_max if vmax is None else vmax
        self._mx_task.CreateAIVoltageChan(ai_path, '', term_cfg.value, vmin.m_as('V'),
                                          vmax.m_as('V'), Val.Volts, '')

    def add_AO_channel(self, ao):
        self._assert_io_type('AO')
        ao_path = ao if isinstance(ao, basestring) else ao.path
        self.chans.append(ao_path)
        min, max = self.daq._max_AO_range()
        self._mx_task.CreateAOVoltageChan(ao_path, '', min.m_as('V'), max.m_as('V'), Val.Volts, '')

    def add_DI_channel(self, di, split_lines=False):
        self._assert_io_type('DI')
        di_path = di if isinstance(di, basestring) else di.path
        chan_paths = di_path.split(',') if split_lines else (di_path,)
        for chan_path in chan_paths:
            self.chans.append(chan_path)
            self._mx_task.CreateDIChan(chan_path, '', Val.ChanForAllLines)

    def add_DO_channel(self, do, split_lines=False):
        self._assert_io_type('DO')
        do_path = do if isinstance(do, basestring) else do.path
        chan_paths = do_path.split(',') if split_lines else (do_path,)
        for chan_path in chan_paths:
            self.chans.append(chan_path)
            self._mx_task.CreateDOChan(chan_path, '', Val.ChanForAllLines)

    def set_AO_only_onboard_mem(self, channel, onboard_only):
        self._mx_task.SetAOUseOnlyOnBrdMem(channel, onboard_only)

    @check_units(timeout='?s')
    def read_AI_scalar(self, timeout=None):
        self._assert_io_type('AI')
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        value = self._mx_task.ReadAnalogScalarF64(timeout_s)
        return Q_(value, 'V')

    @check_units(timeout='?s')
    def read_AI_channels(self, samples=-1, timeout=None):
        """Perform an AI read and get a dict containing the AI buffers"""
        self._assert_io_type('AI')
        samples = int(samples)
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))

        if samples == -1:
            buf_size = self._mx_task.GetBufInputBufSize() * len(self.chans)
        else:
            buf_size = samples * len(self.chans)

        data, n_samples_read = self._mx_task.ReadAnalogF64(samples, timeout_s, Val.GroupByChannel,
                                                           buf_size)
        res = {}
        for i, ch_name in enumerate(self.chans):
            start = i * n_samples_read
            stop = (i+1) * n_samples_read
            res[ch_name] = Q_(data[start:stop], 'V')
        res['t'] = Q_(np.linspace(0, n_samples_read/self.fsamp.m_as('Hz'),
                                  n_samples_read, endpoint=False), 's')
        return res

    @check_units(value='V', timeout='?s')
    def write_AO_scalar(self, value, timeout=None):
        self._assert_io_type('AO')
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        self._mx_task.WriteAnalogScalarF64(True, timeout_s, float(value.m_as('V')))

    @check_units(timeout='?s')
    def read_DI_scalar(self, timeout=None):
        self._assert_io_type('DI')
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        value = self._mx_task.ReadDigitalScalarU32(timeout_s)
        return value

    @check_units(timeout='?s')
    def read_DI_channels(self, samples=-1, timeout=None):
        """Perform a DI read and get a dict containing the DI buffers"""
        self._assert_io_type('DI')
        is_scalar = False  # self.fsamp is None
        samples = int(samples)
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))

        if is_scalar:
            buf_size = 1 * len(self.chans)
        elif samples == -1:
            buf_size = self.input_buf_size * len(self.chans)
        else:
            buf_size = samples * len(self.chans)

        #res = self._mx_task.ReadDigitalLines(samples, timeout_s, Val.GroupByChannel, buf_size)
        #data, n_samples_per_chan_read, n_bytes_per_samp = res
        res = self._mx_task.ReadDigitalU32(samples, timeout_s, Val.GroupByChannel, buf_size)
        data, n_samples_per_chan_read = res
        res = {}
        for i, ch_name in enumerate(self.chans):
            start = i * n_samples_per_chan_read
            stop = (i+1) * n_samples_per_chan_read
            ch_res = data[start] if is_scalar else data[start:stop]
            res[ch_name] = self._reorder_digital_int(ch_res)

        if self.fsamp is not None:
            end_t = (n_samples_per_chan_read-1) / self.fsamp.m_as('Hz')
            res['t'] = Q_(np.linspace(0., end_t, n_samples_per_chan_read), 's')
        return res

    def _reorder_digital_int(self, data):
        """Reorders the bits of a digital int returned by DAQmx based on the line order."""
        # TODO: Support multiple DI channels
        lines = self.chans[0].split(',')
        if len(lines) == 1:
            return data.astype(bool)

        line_pairs = []
        ports = []
        for line_path in lines:
            dev, port, line = line_path.split('/')
            line_pairs.append((port, line))
            if port not in ports:
                ports.append(port)

        port_bytes = {}
        for i, port_name in enumerate(ports):
            port_byte = ((0xFF << 8*i) & data) >> 8*i
            port_bytes[port_name] = port_byte

        out = np.zeros(data.shape)
        for i, (port_name, line_name) in enumerate(line_pairs):
            line_num = int(line_name.replace('line', ''))
            port_byte = port_bytes[port_name]
            out += ((port_byte & (1 << line_num)) >> line_num) << i
        return out

    @check_units(timeout='?s')
    def write_DO_scalar(self, value, timeout=None):
        self._assert_io_type('DO')
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        self._mx_task.WriteDigitalScalarU32(True, timeout_s, value)

    @check_units(timeout='?s')
    def wait_until_done(self, timeout=None):
        """Wait until the task is done

        Parameters
        ----------
        timeout : Quantity, optional
            The maximum amount of time to wait. If None, waits indefinitely. Raises a TimeoutError
            if the timeout is reached.
        """
        timeout_s = float(-1. if timeout is None else timeout.m_as('s'))
        try:
            self._mx_task.WaitUntilTaskDone(timeout_s)
        except DAQError as e:
            if e.code == -200560:
                raise TimeoutError('Task not completed within the given timeout')
            else:
                raise

    def overwrite(self, overwrite):
        """Set whether to overwrite samples in the buffer that have not been read yet."""
        val = Val.OverwriteUnreadSamps if overwrite else Val.DoNotOverwriteUnreadSamps
        self._mx_task.SetReadOverWrite(val)

    @check_enums(relative_to=RelativeTo)
    def relative_to(self, relative_to):
        self._mx_task.SetReadRelativeTo(relative_to.value)

    def offset(self, offset):
        self._mx_task.SetReadOffset(offset)

    def write_AO_channels(self, data, timeout=-1.0, autostart=True):
        if timeout != -1.0:
            timeout = float(Q_(timeout).m_as('s'))
        arr = np.concatenate([data[ao].m_as('V') for ao in self.chans]).astype(np.float64)
        n_samples = len(list(data.values())[0].magnitude)
        self._mx_task.WriteAnalogF64(n_samples, autostart, timeout, Val.GroupByChannel, arr)


class Channel(object):
    def __init__(self, daq):
        # We hold onto the DAQ object as a weakref to avoid cycles in the reference graph. Since
        # Task implements a __del__ method and holds references to channels, the CPython refcounter
        # refuses to clean up the Channel/DAQ cycles when a Task exists. This leads to the DAQ
        # object persisting, and Instrumental will complain that the instrument is already open
        # if you try to re-open it (even though the user thinks it's deleted). See #38 on GitHub.
        self._daqref = weakref.ref(daq)

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if isinstance(other, Channel):
            return self.path == other.path
        else:
            return self.path == other

    @property
    def daq(self):
        daq = self._daqref()
        if daq is None:
            raise RuntimeError("This channel's DAQ object no longer exists")
        return daq


class AnalogIn(Channel):
    type = 'AI'

    def __init__(self, daq, chan_name):
        Channel.__init__(self, daq)
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
        with self.daq._create_mini_task('AI') as mtask:
            mtask.add_AI_channel(self, vmin=vmin, vmax=vmax)

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
                raise ValueError("Must specify 0 or 2 of duration, fsamp, and n_samples")
        return data

    def start_reading(self, fsamp=None, vmin=None, vmax=None, overwrite=False,
                      relative_to=RelativeTo.CurrReadPos, offset=0, buf_size=10):
        self._mtask = mtask = self.daq._create_mini_task('AI')
        mtask.add_AI_channel(self, vmin=vmin, vmax=vmax)
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
        Channel.__init__(self, daq)
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
        with self.daq._create_mini_task('AI') as mtask:
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
                raise ValueError("Must specify 0 or 2 of duration, fsamp, and n_samples")
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
            raise ValueError("Need one and only one of `fsamp` or `freq`")
        if fsamp is None:
            fsamp = freq * len(data)

        if num_not_none(duration, reps) == 2:
            raise ValueError("Can use at most one of `duration` or `reps`, not both")
        if duration is None:
            duration = (reps or 1) * len(data) / fsamp

        fsamp, n_samples = handle_timing_params(duration, fsamp, len(data))

        with self.daq._create_mini_task('AO') as mtask:
            mtask.add_AO_channel(self)
            mtask.set_AO_only_onboard_mem(self.path, onboard)
            mtask.config_timing(fsamp, n_samples)
            mtask.write_AO_channels({self.path: data})
            mtask.wait_until_done()

    def _write_scalar(self, value):
        with self.daq._create_mini_task('AO') as mtask:
            mtask.add_AO_channel(self)
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
        Channel.__init__(self, daq)
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

    @property
    def path(self):
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

    def _add_to_minitask(self, minitask, split_lines=False):
        io_type = self.type if self.type in ('DI', 'DO') else minitask.io_type

        if self.type == 'DI':
            minitask.add_DI_channel(self, split_lines)
        elif self.type == 'DO':
            minitask.add_DO_channel(self, split_lines)
        else:
            raise TypeError("Can't add digital channel to MiniTask of type {}".format(io_type))

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

        port_bytes = {}
        for i, port_name in enumerate(self.ports):
            port_byte = ((0xFF << 8*i) & value) >> 8*i
            port_bytes[port_name] = int(port_byte)

        out = 0
        for i, (port_name, line_name) in enumerate(self.line_pairs):
            line_num = int(line_name.replace('line', ''))
            port_byte = port_bytes[port_name]
            out += ((port_byte & (1 << line_num)) >> line_num) << i
        return out

    @check_units(duration='?s', fsamp='?Hz')
    def read(self, duration=None, fsamp=None, n_samples=None):
        """Read one or more digital input samples.

        - By default, reads and returns a single sample
        - If only `n_samples` is given, uses `OnDemand` (software) timing
        - If two of `duration`, `fsamp`, and `n_samples` are given, uses hardware timing

        Parameters
        ----------
        duration : Quantity
            How long to read from the digital input, specified as a Quantity. Use with `fsamp` or
            `n_samples`.
        fsamp : Quantity
            The sample frequency, specified as a Quantity. Use with `duration` or `n_samples`.
        n_samples : int
            The number of samples to read.

        Returns
        -------
        data : int or int array
            The data that was read from analog output.

        For a single-line channel, each sample is a bool. For a multi-line channel, each sample is
        an int--the lowest bit of the int was read from the first digital line, the second from the
        second line, and so forth.
        """
        with self.daq._create_mini_task('DI') as minitask:
            minitask.add_DI_channel(self)
            num_args_specified = sum(int(arg is not None) for arg in (duration, fsamp, n_samples))

            if num_args_specified == 0:
                data = minitask.read_DI_scalar()
                data = self._parse_DI_int(data)
            elif num_args_specified == 2:
                fsamp, n_samples = handle_timing_params(duration, fsamp, n_samples)
                minitask.config_timing(fsamp, n_samples)
                data = minitask.read_DI_channels()
            elif n_samples is not None:
                data = minitask.read_DI_channels(samples=n_samples)
            else:
                raise ValueError("Must specify nothing, fsamp only, or two of duration, fsamp, "
                                 "and n_samples")
        return data

    def write(self, value):
        """Write a value to the digital output channel

        Parameters
        ----------
        value : int or bool
            An int representing the digital values to write. The lowest bit of
            the int is written to the first digital line, the second to the
            second, and so forth. For a single-line DO channel, can be a bool.
        """
        with self.daq._create_mini_task('DO') as t:
            t.add_DO_channel(self)
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

        with self.daq._create_mini_task('DO') as t:
            t.add_DO_channel(self)
            t.set_DO_only_onboard_mem(self.path, onboard)
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
    _INST_PARAMS_ = ['name', 'serial', 'model']

    mx = NiceNI
    Task = Task

    def _initialize(self):
        self.name = self._paramset['name']
        self._dev = self.mx.Device(self.name)
        self._load_analog_channels()
        self._load_internal_channels()
        self._load_digital_ports()

    def _create_mini_task(self, io_type):
        return MiniTask(self, io_type)

    def _load_analog_channels(self):
        for ai_name in self._basenames(self._dev.GetDevAIPhysicalChans()):
            setattr(self, ai_name, AnalogIn(self, ai_name))

        for ao_name in self._basenames(self._dev.GetDevAOPhysicalChans()):
            setattr(self, ao_name, AnalogOut(self, ao_name))

    def _load_internal_channels(self):
        ch_names = _internal_channels.get(self.product_category, [])
        for ch_name in ch_names:
            setattr(self, ch_name, AnalogIn(self, ch_name))

    def _load_digital_ports(self):
        # Need to handle general case of DI and DO ports, can't assume they're always the same...
        ports = {}
        for line_path in split_list(self._dev.GetDevDILines()):
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
        return [path.rsplit('/', 1)[-1] for path in split_list(names)]

    product_type = property(lambda self: self._dev.GetDevProductType())
    product_category = property(lambda self: ProductCategory(self._dev.GetDevProductCategory()))
    serial = property(lambda self: self._dev.GetDevSerialNum())
