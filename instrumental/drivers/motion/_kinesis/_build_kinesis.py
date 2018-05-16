# -*- coding: utf-8 -*-
# Copyright 2016-2018 Nate Bogdanowicz
from nicelib import build_lib
from nicelib.process import modify_pattern

# shared:
#   TLI (top-level interface?)
#   MOT (motors)
#   NT (NanoTrak)
#   PZ (Piezo)

libs = [
    "Thorlabs.MotionControl.Benchtop.BrushlessMotor",  # MOT, BMC
    "Thorlabs.MotionControl.Benchtop.DCServo",  # MOT, BDC
    "Thorlabs.MotionControl.Benchtop.NanoTrak",  # NT, BNT
    "Thorlabs.MotionControl.Benchtop.Piezo",  # PZ, PBC
    "Thorlabs.MotionControl.Benchtop.PrecisionPiezo",  # PPC, PPC2
    "Thorlabs.MotionControl.Benchtop.StepperMotor",
    #"Thorlabs.MotionControl.Controls",
    #"Thorlabs.MotionControl.DataLogger",
    #"Thorlabs.MotionControl.DeviceManager",
    "Thorlabs.MotionControl.FilterFlipper",
    #"Thorlabs.MotionControl.FTD2xx_Net",
    "Thorlabs.MotionControl.IntegratedStepperMotors",
    #"Thorlabs.MotionControl.Joystick",
    "Thorlabs.MotionControl.KCube.BrushlessMotor",
    "Thorlabs.MotionControl.KCube.DCServo",
    "Thorlabs.MotionControl.KCube.InertialMotor",
    "Thorlabs.MotionControl.KCube.LaserSource",
    "Thorlabs.MotionControl.KCube.NanoTrak",
    "Thorlabs.MotionControl.KCube.Piezo",
    "Thorlabs.MotionControl.KCube.PositionAligner",
    "Thorlabs.MotionControl.KCube.Solenoid",
    "Thorlabs.MotionControl.KCube.StepperMotor",
    ##"Thorlabs.MotionControl.KCube.StrainGauge",
    "Thorlabs.MotionControl.ModularRack",
    "Thorlabs.MotionControl.TCube.BrushlessMotor",
    "Thorlabs.MotionControl.TCube.DCServo",
    "Thorlabs.MotionControl.TCube.InertialMotor",
    "Thorlabs.MotionControl.TCube.LaserDiode",
    "Thorlabs.MotionControl.TCube.LaserSource",
    "Thorlabs.MotionControl.TCube.NanoTrak",
    "Thorlabs.MotionControl.TCube.Piezo",
    "Thorlabs.MotionControl.TCube.Quad",
    "Thorlabs.MotionControl.TCube.Solenoid",
    "Thorlabs.MotionControl.TCube.StepperMotor",
    "Thorlabs.MotionControl.TCube.StrainGauge",
    "Thorlabs.MotionControl.TCube.TEC",
    "Thorlabs.MotionControl.TDIEngine",
    #"Thorlabs.MotionControl.Tools.Common",
    #"Thorlabs.MotionControl.Tools.Logging",
    #"Thorlabs.MotionControl.Tools.WPF",
    "Thorlabs.MotionControl.VerticalStage",
]


def make_info(lib_name):
    header_info = {
        'win*': {
            'path': (
                r"{PROGRAMFILES}\Thorlabs\Kinesis",
                r"{PROGRAMFILES(X86)}\Thorlabs\Kinesis",
            ),
            'header': '{}.h'.format(lib_name)
        },
    }

    lib_names = {'win*': '{}.dll'.format(lib_name)}

    return header_info, lib_names

common_preamble = """
typedef unsigned char byte;
typedef int16_t _int16;

typedef struct tagSAFEARRAYBOUND {
  ULONG cElements;
  LONG  lLbound;
} SAFEARRAYBOUND, *LPSAFEARRAYBOUND;

typedef struct tagSAFEARRAY {
  USHORT         cDims;
  USHORT         fFeatures;
  ULONG          cbElements;
  ULONG          cLocks;
  PVOID          pvData;
  SAFEARRAYBOUND rgsabound[1];
} SAFEARRAY, *LPSAFEARRAY;
"""

tli_header_src = """
typedef enum MOT_MotorTypes
{
    MOT_NotMotor = 0, ///<Not a motor
    MOT_DCMotor = 1, ///< Motor is a DC Servo motor
    MOT_StepperMotor = 2, ///< Motor is a Stepper Motor
    MOT_BrushlessMotor = 3, ///< Motor is a Brushless Motor
    MOT_CustomMotor = 100, ///< Motor is a custom motor
} MOT_MotorTypes;

#pragma pack(1)

typedef struct TLI_DeviceInfo
{
    DWORD typeID;
    char description[65];
    char serialNo[9];
    DWORD PID;

    bool isKnownType;
    MOT_MotorTypes motorType;

    bool isPiezoDevice;
    bool isLaser;
    bool isCustomType;
    bool isRack;
    short maxChannels;
} TLI_DeviceInfo;

typedef struct TLI_HardwareInformation
{
    DWORD serialNumber;
    char modelNumber[8];
    WORD type;
    DWORD firmwareVersion;
    char notes[48];
    BYTE deviceDependantData[12];
    WORD hardwareVersion;
    WORD modificationState;
    short numChannels;
} TLI_HardwareInformation;

short __cdecl TLI_BuildDeviceList(void);
short __cdecl TLI_GetDeviceListSize();
short __cdecl TLI_GetDeviceList(SAFEARRAY** stringsReceiver);
short __cdecl TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID);
short __cdecl TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length);
short __cdecl TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer);
short __cdecl TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID);
short __cdecl TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length);
short __cdecl TLI_GetDeviceInfo(char const * serialNo, TLI_DeviceInfo *info);
"""

# Removing pass-by-ref:
#
# Must be within param-list


def ref_hook(tokens):
    return modify_pattern(tokens, [('k', 'int64_t'), ('d', '&'), ('a', '*'),
                                   ('k', 'lastUpdateTimeMS')])


def scc_hook(tokens):
    """Fixes a (seeming) typo in the ISC header"""
    for token in tokens:
        if token.string == 'SCC_RequestJogParams':
            token.string = 'ISC_RequestJogParams'
        yield token


def build(shortname, sublib):
    ll_module_name = '_{}_lib'.format(shortname)
    header_info, lib_names = make_info(sublib)
    preamble = common_preamble

    # Common DeviceManager library, which doesn't have a header
    if shortname == 'tli':
        header_info = None
        preamble += tli_header_src

    build_lib(header_info, lib_names, ll_module_name, __file__, ignore_system_headers=True,
              preamble=preamble, hook_groups='C++', token_hooks=(scc_hook))


def build_all():
    import os.path
    from nicelib.util import handle_header_path
    from nicelib.process import process_headers
    filedir = os.path.dirname(os.path.abspath(__file__))
    prefixes = {}
    funcs = set()

    for sublib in libs:
        print('Finding {}...'.format(sublib))
        header_info, lib_names = make_info(sublib)
        header_paths, predef_path = handle_header_path(header_info, filedir)
        ret = process_headers(header_paths, predef_path, ignore_system_headers=True,
                              preamble=common_preamble, hook_groups='C++',
                              token_hooks=(ref_hook, scc_hook))
        _, defs, argnames = ret
        prefixes[sublib] = set(n.split('_')[0] for n in argnames)
        for funcname in argnames:
            funcs.add(funcname.split('_', 1)[-1])

    return prefixes, funcs
