# -*- coding: utf-8 -*-
# Copyright 2016-2018 Nate Bogdanowicz
from nicelib import build_lib
from nicelib.process import modify_pattern


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
    ll_module_name = '_kinesis_{}_lib'.format(shortname)
    header_info, lib_names = make_info(sublib)
    preamble = common_preamble

    # Common DeviceManager library, which doesn't have a header
    if shortname == 'tli':
        header_info = None
        preamble += tli_header_src

    build_lib(header_info, lib_names, ll_module_name, __file__, ignore_system_headers=True,
              preamble=preamble, hook_groups='C++', token_hooks=(ref_hook, scc_hook))
