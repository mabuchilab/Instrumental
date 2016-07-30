# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 16:44:14 2015

@author: Lab
"""

# Copyright 2015 Christopher Rogers
"""
Script to Test out the PICAM SDK
"""

from ctypes import WinDLL, CDLL, OleDLL, pointer, POINTER, c_char, c_bool, c_float
from ctypes import c_char_p, cast, Structure, c_int
from ctypes import c_byte, c_int8, c_uint8, c_int16, c_uint16, c_int32, c_uint
from ctypes import c_uint32, c_int64, c_uint64, c_double, c_void_p
from ctypes import create_string_buffer, byref, addressof, c_uint, cast
from ctypes.wintypes import DWORD, INT, ULONG, DOUBLE, HWND
import os.path

# According to Section 1.9, 2.1 and 3.1 of the SDK manual:
piint = c_int
piflt = c_double
pibln = c_bool
pichar = c_char
pibyte = c_byte
pibool = c_bool
pi8s = c_int8
pi8u = c_uint8
pi16s = c_int16
pi16u = c_uint16
pi32s = c_int32
pi32u = c_uint32
pi64s = c_int64
pi64u = c_uint64
pi32f = c_float
pi64f = c_double
PicamModel = c_uint
PicamComputerInterface = c_uint
PicamStringSize = c_int # should this be uint?
PicamError = c_int
PicamEnumeratedType = c_int
PicamHandle = c_void_p
PicamAcquisitionErrorsMask = c_uint

PicamStringSize_SensorName = 64
PicamStringSize_SerialNumber = 64
PicamStringSize_FirmwareName = 64
PicamStringSize_FirmwareDetail = 256
PicamErrorTimeOutOccurred = 32

# from picam.h, we have the Picamenumerated types
PicamEnumeratedType_Error = 1
PicamEnumeratedType_EnumeratedType = 29
PicamEnumeratedType_Model = 2
PicamEnumeratedType_ComputerInterface = 3
PicamEnumeratedType_DiscoveryAction = 26
PicamEnumeratedType_HandleType = 27
PicamEnumeratedType_ValueType = 4
PicamEnumeratedType_ConstraintType = 5
PicamEnumeratedType_Parameter = 6
PicamEnumeratedType_AdcAnalogGain = 7
PicamEnumeratedType_AdcQuality = 8
PicamEnumeratedType_CcdCharacteristicsMask = 9
PicamEnumeratedType_GateTrackingMask = 36
PicamEnumeratedType_GatingMode = 34
PicamEnumeratedType_GatingSpeed = 38
PicamEnumeratedType_EMIccdGainControlMode = 42
PicamEnumeratedType_IntensifierOptionsMask = 35
PicamEnumeratedType_IntensifierStatus = 33
PicamEnumeratedType_ModulationTrackingMask = 41
PicamEnumeratedType_OrientationMask = 10
PicamEnumeratedType_OutputSignal = 11
PicamEnumeratedType_PhosphorType = 39
PicamEnumeratedType_PhotocathodeSensitivity = 40
PicamEnumeratedType_PhotonDetectionMode = 43
PicamEnumeratedType_PixelFormat = 12
PicamEnumeratedType_ReadoutControlMode = 13
PicamEnumeratedType_SensorTemperatureStatus = 14
PicamEnumeratedType_SensorType = 15
PicamEnumeratedType_ShutterTimingMode = 16
PicamEnumeratedType_TimeStampsMask = 17
PicamEnumeratedType_TriggerCoupling = 30
PicamEnumeratedType_TriggerDetermination = 18
PicamEnumeratedType_TriggerResponse = 19
PicamEnumeratedType_TriggerSource = 31
PicamEnumeratedType_TriggerTermination = 32
PicamEnumeratedType_ValueAccess = 20
PicamEnumeratedType_DynamicsMask = 28
PicamEnumeratedType_ConstraintScope = 21
PicamEnumeratedType_ConstraintSeverity = 22
PicamEnumeratedType_ConstraintCategory = 23
PicamEnumeratedType_RoisConstraintRulesMask = 24
PicamEnumeratedType_AcquisitionErrorsMask = 25

# From picam.h, we also have
# enum PicamValueType
PicamValueType_Integer = 1
PicamValueType_Boolean = 3
PicamValueType_Enumeration = 4
PicamValueType_LargeInteger = 6
PicamValueType_FloatingPoint = 2
PicamValueType_Rois = 5
PicamValueType_Pulse = 7
PicamValueType_Modulations = 8

# enum PicamConstraintType
PicamConstraintType_None = 1
PicamConstraintType_Range = 2
PicamConstraintType_Collection = 3
PicamConstraintType_Rois = 4
PicamConstraintType_Pulse = 5
PicamConstraintType_Modulations = 6

#Camera Identification -----------------------------------------------------*/

PicamModel_PixisSeries              =    0
#/* PIXIS 100 Series ------------------------------------------------------*/
PicamModel_Pixis100Series           =    1
PicamModel_Pixis100F                =    2
PicamModel_Pixis100B                =    6
PicamModel_Pixis100R                =    3
PicamModel_Pixis100C                =    4
PicamModel_Pixis100BR               =    5
PicamModel_Pixis100BExcelon         =   54
PicamModel_Pixis100BRExcelon        =   55
PicamModel_PixisXO100B              =    7
PicamModel_PixisXO100BR             =    8
PicamModel_PixisXB100B              =   68
PicamModel_PixisXB100BR             =   69
#/* PIXIS 256 Series ------------------------------------------------------*/
PicamModel_Pixis256Series           =   26
PicamModel_Pixis256F                =   27
PicamModel_Pixis256B                =   29
PicamModel_Pixis256E                =   28
PicamModel_Pixis256BR               =   30
PicamModel_PixisXB256BR             =   31
#/* PIXIS 400 Series ------------------------------------------------------*/
PicamModel_Pixis400Series           =   37
PicamModel_Pixis400F                =   38
PicamModel_Pixis400B                =   40
PicamModel_Pixis400R                =   39
PicamModel_Pixis400BR               =   41
PicamModel_Pixis400BExcelon         =   56
PicamModel_Pixis400BRExcelon        =   57
PicamModel_PixisXO400B              =   42
PicamModel_PixisXB400BR             =   70
#/* PIXIS 512 Series ------------------------------------------------------*/
PicamModel_Pixis512Series           =   43
PicamModel_Pixis512F                =   44
PicamModel_Pixis512B                =   45
PicamModel_Pixis512BUV              =   46
PicamModel_Pixis512BExcelon         =   58
PicamModel_PixisXO512F              =   49
PicamModel_PixisXO512B              =   50
PicamModel_PixisXF512F              =   48
PicamModel_PixisXF512B              =   47
#/* PIXIS 1024 Series -----------------------------------------------------*/
PicamModel_Pixis1024Series          =    9
PicamModel_Pixis1024F               =   10
PicamModel_Pixis1024B               =   11
PicamModel_Pixis1024BR              =   13
PicamModel_Pixis1024BUV             =   12
PicamModel_Pixis1024BExcelon        =   59
PicamModel_Pixis1024BRExcelon       =   60
PicamModel_PixisXO1024F             =   16
PicamModel_PixisXO1024B             =   14
PicamModel_PixisXO1024BR            =   15
PicamModel_PixisXF1024F             =   17
PicamModel_PixisXF1024B             =   18
PicamModel_PixisXB1024BR            =   71
#/* PIXIS 1300 Series -----------------------------------------------------*/
PicamModel_Pixis1300Series          =   51
PicamModel_Pixis1300F               =   52
PicamModel_Pixis1300F_2             =   75
PicamModel_Pixis1300B               =   53
PicamModel_Pixis1300BR              =   73
PicamModel_Pixis1300BExcelon        =   61
PicamModel_Pixis1300BRExcelon       =   62
PicamModel_PixisXO1300B             =   65
PicamModel_PixisXF1300B             =   66
PicamModel_PixisXB1300R             =   72
#/* PIXIS 2048 Series -----------------------------------------------------*/
PicamModel_Pixis2048Series          =   20
PicamModel_Pixis2048F               =   21
PicamModel_Pixis2048B               =   22
PicamModel_Pixis2048BR              =   67
PicamModel_Pixis2048BExcelon        =   63
PicamModel_Pixis2048BRExcelon       =   74
PicamModel_PixisXO2048B             =   23
PicamModel_PixisXF2048F             =   25
PicamModel_PixisXF2048B             =   24
#/* PIXIS 2K Series -------------------------------------------------------*/
PicamModel_Pixis2KSeries            =   32
PicamModel_Pixis2KF                 =   33
PicamModel_Pixis2KB                 =   34
PicamModel_Pixis2KBUV               =   36
PicamModel_Pixis2KBExcelon          =   64
PicamModel_PixisXO2KB               =   35
#/* Quad-RO Series (104) --------------------------------------------------*/
PicamModel_QuadroSeries             =  100
PicamModel_Quadro4096               =  101
PicamModel_Quadro4096_2             =  103
PicamModel_Quadro4320               =  102
#/* ProEM Series (214) ----------------------------------------------------*/
PicamModel_ProEMSeries              =  200
#/* ProEM 512 Series ------------------------------------------------------*/
PicamModel_ProEM512Series           =  203
PicamModel_ProEM512B                =  201
PicamModel_ProEM512BK               =  205
PicamModel_ProEM512BExcelon         =  204
PicamModel_ProEM512BKExcelon        =  206
#/* ProEM 1024 Series -----------------------------------------------------*/
PicamModel_ProEM1024Series          =  207
PicamModel_ProEM1024B               =  202
PicamModel_ProEM1024BExcelon        =  208
#/* ProEM 1600 Series -----------------------------------------------------*/
PicamModel_ProEM1600Series          =  209
PicamModel_ProEM1600xx2B            =  212
PicamModel_ProEM1600xx2BExcelon     =  210
PicamModel_ProEM1600xx4B            =  213
PicamModel_ProEM1600xx4BExcelon     =  211
#/* ProEM+ Series (614) ---------------------------------------------------*/
PicamModel_ProEMPlusSeries          =  600
#/* ProEM+ 512 Series -----------------------------------------------------*/
PicamModel_ProEMPlus512Series       =  603
PicamModel_ProEMPlus512B            =  601
PicamModel_ProEMPlus512BK           =  605
PicamModel_ProEMPlus512BExcelon     =  604
PicamModel_ProEMPlus512BKExcelon    =  606
#/* ProEM+ 1024 Series ----------------------------------------------------*/
PicamModel_ProEMPlus1024Series      =  607
PicamModel_ProEMPlus1024B           =  602
PicamModel_ProEMPlus1024BExcelon    =  608
#/* ProEM+ 1600 Series ----------------------------------------------------*/
PicamModel_ProEMPlus1600Series      =  609
PicamModel_ProEMPlus1600xx2B        =  612
PicamModel_ProEMPlus1600xx2BExcelon =  610
PicamModel_ProEMPlus1600xx4B        =  613
PicamModel_ProEMPlus1600xx4BExcelon =  611
#/* ProEM-HS Series (1209) ------------------------------------------------*/
PicamModel_ProEMHSSeries            = 1200
#/* ProEM-HS 512 Series ---------------------------------------------------*/
PicamModel_ProEMHS512Series         = 1201
PicamModel_ProEMHS512B              = 1202
PicamModel_ProEMHS512BK             = 1207
PicamModel_ProEMHS512BExcelon       = 1203
PicamModel_ProEMHS512BKExcelon      = 1208
#/* ProEM-HS 1024 Series --------------------------------------------------*/
PicamModel_ProEMHS1024Series        = 1204
PicamModel_ProEMHS1024B             = 1205
PicamModel_ProEMHS1024BExcelon      = 1206
#/* PI-MAX3 Series (303) --------------------------------------------------*/
PicamModel_PIMax3Series             =  300
PicamModel_PIMax31024I              =  301
PicamModel_PIMax31024x256           =  302
#/* PI-MAX4 Series (721) --------------------------------------------------*/
PicamModel_PIMax4Series             =  700
#/* PI-MAX4 1024i Series --------------------------------------------------*/
PicamModel_PIMax41024ISeries        =  703
PicamModel_PIMax41024I              =  701
PicamModel_PIMax41024IRF            =  704
#/* PI-MAX4 1024f Series --------------------------------------------------*/
PicamModel_PIMax41024FSeries        =  710
PicamModel_PIMax41024F              =  711
PicamModel_PIMax41024FRF            =  712
#/* PI-MAX4 1024x256 Series -----------------------------------------------*/
PicamModel_PIMax41024x256Series     =  705
PicamModel_PIMax41024x256           =  702
PicamModel_PIMax41024x256RF         =  706
#/* PI-MAX4 2048 Series ---------------------------------------------------*/
PicamModel_PIMax42048Series         =  716
PicamModel_PIMax42048F              =  717
PicamModel_PIMax42048B              =  718
PicamModel_PIMax42048FRF            =  719
PicamModel_PIMax42048BRF            =  720
#/* PI-MAX4 512EM Series --------------------------------------------------*/
PicamModel_PIMax4512EMSeries        =  708
PicamModel_PIMax4512EM              =  707
PicamModel_PIMax4512BEM             =  709
#/* PI-MAX4 1024EM Series -------------------------------------------------*/
PicamModel_PIMax41024EMSeries       =  713
PicamModel_PIMax41024EM             =  715
PicamModel_PIMax41024BEM            =  714
#/* PyLoN Series (439) ----------------------------------------------------*/
PicamModel_PylonSeries              =  400
#/* PyLoN 100 Series ------------------------------------------------------*/
PicamModel_Pylon100Series           =  418
PicamModel_Pylon100F                =  404
PicamModel_Pylon100B                =  401
PicamModel_Pylon100BR               =  407
PicamModel_Pylon100BExcelon         =  425
PicamModel_Pylon100BRExcelon        =  426
#/* PyLoN 256 Series ------------------------------------------------------*/
PicamModel_Pylon256Series           =  419
PicamModel_Pylon256F                =  409
PicamModel_Pylon256B                =  410
PicamModel_Pylon256E                =  411
PicamModel_Pylon256BR               =  412
#/* PyLoN 400 Series ------------------------------------------------------*/
PicamModel_Pylon400Series           =  420
PicamModel_Pylon400F                =  405
PicamModel_Pylon400B                =  402
PicamModel_Pylon400BR               =  408
PicamModel_Pylon400BExcelon         =  427
PicamModel_Pylon400BRExcelon        =  428
#/* PyLoN 1024 Series -----------------------------------------------------*/
PicamModel_Pylon1024Series          =  421
PicamModel_Pylon1024B               =  417
PicamModel_Pylon1024BExcelon        =  429
#/* PyLoN 1300 Series -----------------------------------------------------*/
PicamModel_Pylon1300Series          =  422
PicamModel_Pylon1300F               =  406
PicamModel_Pylon1300B               =  403
PicamModel_Pylon1300R               =  438
PicamModel_Pylon1300BR              =  432
PicamModel_Pylon1300BExcelon        =  430
PicamModel_Pylon1300BRExcelon       =  433
#/* PyLoN 2048 Series -----------------------------------------------------*/
PicamModel_Pylon2048Series          =  423
PicamModel_Pylon2048F               =  415
PicamModel_Pylon2048B               =  434
PicamModel_Pylon2048BR              =  416
PicamModel_Pylon2048BExcelon        =  435
PicamModel_Pylon2048BRExcelon       =  436
#/* PyLoN 2K Series -------------------------------------------------------*/
PicamModel_Pylon2KSeries            =  424
PicamModel_Pylon2KF                 =  413
PicamModel_Pylon2KB                 =  414
PicamModel_Pylon2KBUV               =  437
PicamModel_Pylon2KBExcelon          =  431
#/* PyLoN-IR Series (904) -------------------------------------------------*/
PicamModel_PylonirSeries            =  900
#/* PyLoN-IR 1024 Series --------------------------------------------------*/
PicamModel_Pylonir1024Series        =  901
PicamModel_Pylonir102422            =  902
PicamModel_Pylonir102417            =  903
#/* PIoNIR Series (502) ---------------------------------------------------*/
PicamModel_PionirSeries             =  500
PicamModel_Pionir640                =  501
#/* NIRvana Series (802) --------------------------------------------------*/
PicamModel_NirvanaSeries            =  800
PicamModel_Nirvana640               =  801
#/* NIRvana ST Series (1302) ----------------------------------------------*/
PicamModel_NirvanaSTSeries          = 1300
PicamModel_NirvanaST640             = 1301
#/* NIRvana-LN Series (1102) ----------------------------------------------*/
PicamModel_NirvanaLNSeries          = 1100
PicamModel_NirvanaLN640             = 1101

# enum PicamParameter


def pi_v(v,c,n):
    return (c << 24)+(v << 16)+n


PicamParameter_ExposureTime                      = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        23)
PicamParameter_ShutterTimingMode                 = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   24)
PicamParameter_ShutterOpeningDelay               = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        46)
PicamParameter_ShutterClosingDelay               = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        25)
PicamParameter_ShutterDelayResolution            = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Collection,   47)
PicamParameter_EnableIntensifier                 = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   86)
PicamParameter_IntensifierStatus                 = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,         87)
PicamParameter_IntensifierGain                   = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        88)
PicamParameter_EMIccdGainControlMode             = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,  123)
PicamParameter_EMIccdGain                        = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,       124)
PicamParameter_PhosphorDecayDelay                = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        89)
PicamParameter_PhosphorDecayDelayResolution      = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Collection,   90)
PicamParameter_GatingMode                        = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   93)
PicamParameter_RepetitiveGate                    = pi_v(PicamValueType_Pulse,         PicamConstraintType_Pulse,        94)
PicamParameter_SequentialStartingGate            = pi_v(PicamValueType_Pulse,         PicamConstraintType_Pulse,        95)
PicamParameter_SequentialEndingGate              = pi_v(PicamValueType_Pulse,         PicamConstraintType_Pulse,        96)
PicamParameter_SequentialGateStepCount           = pi_v(PicamValueType_LargeInteger,  PicamConstraintType_Range,        97)
PicamParameter_SequentialGateStepIterations      = pi_v(PicamValueType_LargeInteger,  PicamConstraintType_Range,        98)
PicamParameter_DifStartingGate                   = pi_v(PicamValueType_Pulse,         PicamConstraintType_Pulse,       102)
PicamParameter_DifEndingGate                     = pi_v(PicamValueType_Pulse,         PicamConstraintType_Pulse,       103)
PicamParameter_BracketGating                     = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,  100)
PicamParameter_IntensifierOptions                = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,        101)
PicamParameter_EnableModulation                  = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,  111)
PicamParameter_ModulationDuration                = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       118)
PicamParameter_ModulationFrequency               = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       112)
PicamParameter_RepetitiveModulationPhase         = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       113)
PicamParameter_SequentialStartingModulationPhase = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       114)
PicamParameter_SequentialEndingModulationPhase   = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       115)
PicamParameter_CustomModulationSequence          = pi_v(PicamValueType_Modulations,   PicamConstraintType_Modulations, 119)
PicamParameter_PhotocathodeSensitivity           = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,        107)
PicamParameter_GatingSpeed                       = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,        108)
PicamParameter_PhosphorType                      = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,        109)
PicamParameter_IntensifierDiameter               = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,        110)
PicamParameter_AdcSpeed                          = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Collection,   33)
PicamParameter_AdcBitDepth                       = pi_v(PicamValueType_Integer,       PicamConstraintType_Collection,   34)
PicamParameter_AdcAnalogGain                     = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   35)
PicamParameter_AdcQuality                        = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   36)
PicamParameter_AdcEMGain                         = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        53)
PicamParameter_CorrectPixelBias                  = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,  106)
PicamParameter_TriggerSource                     = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   79)
PicamParameter_TriggerResponse                   = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   30)
PicamParameter_TriggerDetermination              = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   31)
PicamParameter_TriggerFrequency                  = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        80)
PicamParameter_TriggerTermination                = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   81)
PicamParameter_TriggerCoupling                   = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   82)
PicamParameter_TriggerThreshold                  = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        83)
PicamParameter_OutputSignal                      = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   32)
PicamParameter_InvertOutputSignal                = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   52)
PicamParameter_AuxOutput                         = pi_v(PicamValueType_Pulse,         PicamConstraintType_Pulse,        91)
PicamParameter_EnableSyncMaster                  = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   84)
PicamParameter_SyncMaster2Delay                  = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        85)
PicamParameter_EnableModulationOutputSignal      = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,  116)
PicamParameter_ModulationOutputSignalFrequency   = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       117)
PicamParameter_ModulationOutputSignalAmplitude   = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       120)
PicamParameter_ReadoutControlMode                = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   26)
PicamParameter_ReadoutTimeCalculation            = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         27)
PicamParameter_ReadoutPortCount                  = pi_v(PicamValueType_Integer,       PicamConstraintType_Collection,   28)
PicamParameter_ReadoutOrientation                = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,         54)
PicamParameter_KineticsWindowHeight              = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        56)
PicamParameter_VerticalShiftRate                 = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Collection,   13)
PicamParameter_Accumulations                     = pi_v(PicamValueType_LargeInteger,  PicamConstraintType_Range,        92)
PicamParameter_EnableNondestructiveReadout       = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,  128)
PicamParameter_NondestructiveReadoutPeriod       = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       129)
PicamParameter_Rois                              = pi_v(PicamValueType_Rois,          PicamConstraintType_Rois,         37)
PicamParameter_NormalizeOrientation              = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   39)
PicamParameter_DisableDataFormatting             = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   55)
PicamParameter_ReadoutCount                      = pi_v(PicamValueType_LargeInteger,  PicamConstraintType_Range,        40)
PicamParameter_ExactReadoutCountMaximum          = pi_v(PicamValueType_LargeInteger,  PicamConstraintType_None,         77)
PicamParameter_PhotonDetectionMode               = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,  125)
PicamParameter_PhotonDetectionThreshold          = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,       126)
PicamParameter_PixelFormat                       = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   41)
PicamParameter_FrameSize                         = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         42)
PicamParameter_FrameStride                       = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         43)
PicamParameter_FramesPerReadout                  = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         44)
PicamParameter_ReadoutStride                     = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         45)
PicamParameter_PixelBitDepth                     = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         48)
PicamParameter_ReadoutRateCalculation            = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         50)
PicamParameter_OnlineReadoutRateCalculation      = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         99)
PicamParameter_FrameRateCalculation              = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         51)
PicamParameter_Orientation                       = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,         38)
PicamParameter_TimeStamps                        = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,   68)
PicamParameter_TimeStampResolution               = pi_v(PicamValueType_LargeInteger,  PicamConstraintType_Collection,   69)
PicamParameter_TimeStampBitDepth                 = pi_v(PicamValueType_Integer,       PicamConstraintType_Collection,   70)
PicamParameter_TrackFrames                       = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   71)
PicamParameter_FrameTrackingBitDepth             = pi_v(PicamValueType_Integer,       PicamConstraintType_Collection,   72)
PicamParameter_GateTracking                      = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,  104)
PicamParameter_GateTrackingBitDepth              = pi_v(PicamValueType_Integer,       PicamConstraintType_Collection,  105)
PicamParameter_ModulationTracking                = pi_v(PicamValueType_Enumeration,   PicamConstraintType_Collection,  121)
PicamParameter_ModulationTrackingBitDepth        = pi_v(PicamValueType_Integer,       PicamConstraintType_Collection,  122)
PicamParameter_SensorType                        = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,         57)
PicamParameter_CcdCharacteristics                = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,         58)
PicamParameter_SensorActiveWidth                 = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         59)
PicamParameter_SensorActiveHeight                = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         60)
PicamParameter_SensorActiveLeftMargin            = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         61)
PicamParameter_SensorActiveTopMargin             = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         62)
PicamParameter_SensorActiveRightMargin           = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         63)
PicamParameter_SensorActiveBottomMargin          = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         64)
PicamParameter_SensorMaskedHeight                = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         65)
PicamParameter_SensorMaskedTopMargin             = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         66)
PicamParameter_SensorMaskedBottomMargin          = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         67)
PicamParameter_SensorSecondaryMaskedHeight       = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         49)
PicamParameter_SensorSecondaryActiveHeight       = pi_v(PicamValueType_Integer,       PicamConstraintType_None,         74)
PicamParameter_PixelWidth                        = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,          9)
PicamParameter_PixelHeight                       = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         10)
PicamParameter_PixelGapWidth                     = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         11)
PicamParameter_PixelGapHeight                    = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         12)
PicamParameter_ActiveWidth                       = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         1)
PicamParameter_ActiveHeight                      = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         2)
PicamParameter_ActiveLeftMargin                  = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         3)
PicamParameter_ActiveTopMargin                   = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         4)
PicamParameter_ActiveRightMargin                 = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         5)
PicamParameter_ActiveBottomMargin                = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         6)
PicamParameter_MaskedHeight                      = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         7)
PicamParameter_MaskedTopMargin                   = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,         8)
PicamParameter_MaskedBottomMargin                = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        73)
PicamParameter_SecondaryMaskedHeight             = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        75)
PicamParameter_SecondaryActiveHeight             = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        76)
PicamParameter_CleanSectionFinalHeight           = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        17)
PicamParameter_CleanSectionFinalHeightCount      = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        18)
PicamParameter_CleanSerialRegister               = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   19)
PicamParameter_CleanCycleCount                   = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        20)
PicamParameter_CleanCycleHeight                  = pi_v(PicamValueType_Integer,       PicamConstraintType_Range,        21)
PicamParameter_CleanBeforeExposure               = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   78)
PicamParameter_CleanUntilTrigger                 = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   22)
PicamParameter_SensorTemperatureSetPoint         = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_Range,        14)
PicamParameter_SensorTemperatureReading          = pi_v(PicamValueType_FloatingPoint, PicamConstraintType_None,         15)
PicamParameter_SensorTemperatureStatus           = pi_v(PicamValueType_Enumeration,   PicamConstraintType_None,         16)
PicamParameter_DisableCoolingFan                 = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,   29)
PicamParameter_EnableSensorWindowHeater          = pi_v(PicamValueType_Boolean,       PicamConstraintType_Collection,  127)

# enum PicamAdcAnalogGain
PicamAdcAnalogGain_Low    = 1
PicamAdcAnalogGain_Medium = 2
PicamAdcAnalogGain_High   = 3

# enum PicamAdcQuality
PicamAdcQuality_LowNoise           = 1
PicamAdcQuality_HighCapacity       = 2
PicamAdcQuality_HighSpeed          = 4
PicamAdcQuality_ElectronMultiplied = 3

# enum PicamCcdCharacteristicsMask
PicamCcdCharacteristicsMask_None                 = 0x000
PicamCcdCharacteristicsMask_BackIlluminated      = 0x001
PicamCcdCharacteristicsMask_DeepDepleted         = 0x002
PicamCcdCharacteristicsMask_OpenElectrode        = 0x004
PicamCcdCharacteristicsMask_UVEnhanced           = 0x008
PicamCcdCharacteristicsMask_ExcelonEnabled       = 0x010
PicamCcdCharacteristicsMask_SecondaryMask        = 0x020
PicamCcdCharacteristicsMask_Multiport            = 0x040
PicamCcdCharacteristicsMask_AdvancedInvertedMode = 0x080
PicamCcdCharacteristicsMask_HighResistivity      = 0x100

# enum PicamEMIccdGainControlMode
PicamEMIccdGainControlMode_Optimal = 1
PicamEMIccdGainControlMode_Manual  = 2

# enum PicamGateTrackingMask
PicamGateTrackingMask_None  = 0x0
PicamGateTrackingMask_Delay = 0x1
PicamGateTrackingMask_Width = 0x2

# enum PicamGatingMode
PicamGatingMode_Repetitive = 1
PicamGatingMode_Sequential = 2
PicamGatingMode_Custom     = 3

# enum PicamGatingSpeed
PicamGatingSpeed_Fast = 1
PicamGatingSpeed_Slow = 2

# enum PicamIntensifierOptionsMask
PicamIntensifierOptionsMask_None                = 0x0
PicamIntensifierOptionsMask_McpGating           = 0x1
PicamIntensifierOptionsMask_SubNanosecondGating = 0x2
PicamIntensifierOptionsMask_Modulation          = 0x4

# enum PicamIntensifierStatus
PicamIntensifierStatus_PoweredOff = 1
PicamIntensifierStatus_PoweredOn  = 2

# enum PicamModulationTrackingMask
PicamModulationTrackingMask_None                  = 0x0
PicamModulationTrackingMask_Duration              = 0x1
PicamModulationTrackingMask_Frequency             = 0x2
PicamModulationTrackingMask_Phase                 = 0x4
PicamModulationTrackingMask_OutputSignalFrequency = 0x8

# enum PicamOrientationMask
PicamOrientationMask_Normal              = 0x0
PicamOrientationMask_FlippedHorizontally = 0x1
PicamOrientationMask_FlippedVertically   = 0x2

# enum PicamOutputSignal
PicamOutputSignal_NotReadingOut       =  1
PicamOutputSignal_ShutterOpen         =  2
PicamOutputSignal_Busy                =  3
PicamOutputSignal_AlwaysLow           =  4
PicamOutputSignal_AlwaysHigh          =  5
PicamOutputSignal_Acquiring           =  6
PicamOutputSignal_ShiftingUnderMask   =  7
PicamOutputSignal_Exposing            =  8
PicamOutputSignal_EffectivelyExposing =  9
PicamOutputSignal_ReadingOut          = 10
PicamOutputSignal_WaitingForTrigger   = 11

# enum PicamPhosphorType
PicamPhosphorType_P43 = 1
PicamPhosphorType_P46 = 2

# enum PicamPhotocathodeSensitivity
PicamPhotocathodeSensitivity_RedBlue          =  1
PicamPhotocathodeSensitivity_SuperRed         =  7
PicamPhotocathodeSensitivity_SuperBlue        =  2
PicamPhotocathodeSensitivity_UV               =  3
PicamPhotocathodeSensitivity_SolarBlind       = 10
PicamPhotocathodeSensitivity_Unigen2Filmless  =  4
PicamPhotocathodeSensitivity_InGaAsFilmless   =  9
PicamPhotocathodeSensitivity_HighQEFilmless   =  5
PicamPhotocathodeSensitivity_HighRedFilmless  =  8
PicamPhotocathodeSensitivity_HighBlueFilmless =  6

# enum PicamPhotonDetectionMode
PicamPhotonDetectionMode_Disabled     = 1
PicamPhotonDetectionMode_Thresholding = 2
PicamPhotonDetectionMode_Clipping     = 3

# enum PicamPixelFormat
PicamPixelFormat_Monochrome16Bit = 1

# enum PicamReadoutControlMode
PicamReadoutControlMode_FullFrame       = 1
PicamReadoutControlMode_FrameTransfer   = 2
PicamReadoutControlMode_Interline       = 5
PicamReadoutControlMode_Kinetics        = 3
PicamReadoutControlMode_SpectraKinetics = 4
PicamReadoutControlMode_Dif             = 6

# enum PicamSensorTemperatureStatus
PicamSensorTemperatureStatus_Unlocked = 1
PicamSensorTemperatureStatus_Locked   = 2

# enum PicamSensorType
PicamSensorType_Ccd    = 1
PicamSensorType_InGaAs = 2

# enum PicamShutterTimingMode
PicamShutterTimingMode_Normal            = 1
PicamShutterTimingMode_AlwaysClosed      = 2
PicamShutterTimingMode_AlwaysOpen        = 3
PicamShutterTimingMode_OpenBeforeTrigger = 4

# enum PicamTimeStampsMask
PicamTimeStampsMask_None            = 0x0
PicamTimeStampsMask_ExposureStarted = 0x1
PicamTimeStampsMask_ExposureEnded   = 0x2

# enum PicamTriggerCoupling
PicamTriggerCoupling_AC = 1
PicamTriggerCoupling_DC = 2

# enum PicamTriggerDetermination
PicamTriggerDetermination_PositivePolarity = 1
PicamTriggerDetermination_NegativePolarity = 2
PicamTriggerDetermination_RisingEdge       = 3
PicamTriggerDetermination_FallingEdge      = 4

# enum PicamTriggerResponse
PicamTriggerResponse_NoResponse               = 1
PicamTriggerResponse_ReadoutPerTrigger        = 2
PicamTriggerResponse_ShiftPerTrigger          = 3
PicamTriggerResponse_ExposeDuringTriggerPulse = 4
PicamTriggerResponse_StartOnSingleTrigger     = 5

# enum PicamTriggerSource
PicamTriggerSource_External = 1
PicamTriggerSource_Internal = 2

# enum PicamTriggerTermination
PicamTriggerTermination_FiftyOhms     = 1
PicamTriggerTermination_HighImpedance = 2

# enum PicamValueAccess
PicamValueAccess_ReadOnly         = 1
PicamValueAccess_ReadWriteTrivial = 3
PicamValueAccess_ReadWrite        = 2

# enum PicamConstraintScope
PicamConstraintScope_Independent = 1
PicamConstraintScope_Dependent   = 2

# enum PicamConstraintSeverity
PicamConstraintSeverity_Error   = 1
PicamConstraintSeverity_Warning = 2

# enum PicamConstraintCategory
PicamConstraintCategory_Capable     = 1
PicamConstraintCategory_Required    = 2
PicamConstraintCategory_Recommended = 3

# enum PicamRoisConstraintRulesMask
PicamRoisConstraintRulesMask_None                  = 0x00
PicamRoisConstraintRulesMask_XBinningAlignment     = 0x01
PicamRoisConstraintRulesMask_YBinningAlignment     = 0x02
PicamRoisConstraintRulesMask_HorizontalSymmetry    = 0x04
PicamRoisConstraintRulesMask_VerticalSymmetry      = 0x08
PicamRoisConstraintRulesMask_SymmetryBoundsBinning = 0x10

PicamConstraintSeverity = c_uint
PicamRoisConstraintRulesMask = c_uint
PicamRangeConstraint = c_uint
PicamConstraintScope = c_uint


class PicamRoi(Structure):
    _fields_ = [('x', piint),
                ('width', piint),
                ('x_binning', piint),
                ('y', piint),
                ('height', piint),
                ('y_binning', piint)]


class PicamRois(Structure):
    _fields_ = [('roi_array', c_void_p),
                ('roi_count', piint)]


class PicamRoisConstraint(Structure):
    _fields_ = [('scope', PicamConstraintScope),
                ('severity', PicamConstraintSeverity),
                ('empty_set', pibln),
                ('rules', PicamRoisConstraintRulesMask),
                ('maximum_roi_count', piint),
                ('x_constraint', PicamRangeConstraint),
                ('width_constraint', PicamRangeConstraint),
                ('x_binning_limits_array', POINTER(piint)),
                ('x_binning_limits_count', piint),
                ('y_constraint', PicamRangeConstraint),
                ('height_constraint', PicamRangeConstraint),
                ('y_binning_limits_array', POINTER(piint)),
                ('y_binning_limits_count', piint)]


class PicamPulseConstraint(Structure):
    _fields_ = [('scope', PicamConstraintScope),
                ('severity', PicamConstraintSeverity),
                ('empty_set', pibln),
                ('delay_constraint', PicamRangeConstraint),
                ('width_constraint', PicamRangeConstraint),
                ('minimum_duration', piflt),
                ('maximum_duration', piflt)]


class PicamModulationsConstraint(Structure):
    _fields_ = [('scope', PicamConstraintScope),
                ('severity', PicamConstraintSeverity),
                ('empty_set', pibln),
                ('maximum_modulation_count', piint),
                ('duration_constraint', PicamRangeConstraint),
                ('frequency_constraint', PicamRangeConstraint),
                ('phase_constraint', PicamRangeConstraint),
                ('output_signal_frequency_constraint', PicamRangeConstraint)]


class PicamCollectionConstraint(Structure):
    _fields_ = [('scope', PicamConstraintScope),
                ('severity', PicamConstraintSeverity),
                ('values_array', POINTER(piflt)),
                ('values_count', piint)]


class PicamRangeConstraint(Structure):
    _fields_ = [('scope', PicamConstraintScope),
                ('severity', PicamConstraintSeverity),
                ('empty_set', pibln),
                ('minimum', piflt),
                ('maximum', piflt),
                ('increment', piflt),
                ('excluded_values_array', POINTER(piflt)),
                ('excluded_values_count', piint),
                ('outlying_values_array', POINTER(piflt)),
                ('outlying_values_count', piint)]


class PicamCameraID(Structure):
    _fields_ = [('model', PicamModel),
                ('computer_interface', PicamComputerInterface),
                ('sensor_name', pichar * PicamStringSize_SensorName),
                ('serial_number', pichar * PicamStringSize_SerialNumber)]


class PicamAvailableData(Structure):
    _fields_ = [('initial_readout', c_void_p),
                ('readout_count', pi64s)]


class PicamAcquisitionStatus(Structure):
    _fields_ = [('running', pibln),
                ('errors', PicamAcquisitionErrorsMask),
                ('readout_rate', piflt)]

class PicamFirmwareDetail(Structure):
    _fields_ = [('name', pichar * PicamStringSize_FirmwareName),
                ('detail', pichar * PicamStringSize_FirmwareDetail)]