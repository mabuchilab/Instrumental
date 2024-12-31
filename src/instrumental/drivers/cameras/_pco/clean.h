# 1 "test.h"
# 1 "<command-line>"
# 1 "test.h"




typedef unsigned long ULONG;
typedef ULONG *PULONG;
typedef unsigned short USHORT;
typedef USHORT *PUSHORT;
typedef unsigned char UCHAR;
typedef UCHAR *PUCHAR;
typedef char *PSZ;
typedef int WINBOOL;
typedef int BOOL;
typedef WINBOOL *PBOOL;
typedef WINBOOL *LPBOOL;
typedef unsigned char BYTE;
typedef unsigned short WORD;
typedef unsigned long DWORD;
typedef float FLOAT;
typedef FLOAT *PFLOAT;
typedef BYTE *PBYTE;
typedef BYTE *LPBYTE;
typedef int *PINT;
typedef int *LPINT;
typedef WORD *PWORD;
typedef WORD *LPWORD;
typedef long *LPLONG;
typedef DWORD *PDWORD;
typedef DWORD *LPDWORD;
typedef void *LPVOID;
typedef const void *LPCVOID;
typedef int INT;
typedef unsigned int UINT;
typedef unsigned int *PUINT;


# 1 "headers/sc2_SDKStructures.h" 1
# 153 "headers/sc2_SDKStructures.h"
typedef struct
{
 SHORT sBufNr;
 WORD ZZwAlignDummy;
 DWORD dwStatusDll;
 DWORD dwStatusDrv;
}PCO_Buflist;

typedef struct
{
  WORD wSize;
  WORD wInterfaceType;


  WORD wCameraNumber;



  WORD wCameraNumAtInterface;
  WORD wOpenFlags[10];






  DWORD dwOpenFlags[5];
  void* wOpenPtr[6];
  WORD zzwDummy[8];
}PCO_OpenStruct;

typedef struct
{
  char szName[16];
  WORD wBatchNo;
  WORD wRevision;
  WORD wVariant;
  WORD ZZwDummy[20];
}
PCO_SC2_Hardware_DESC;

typedef struct
{
  char szName[16];
  BYTE bMinorRev;
  BYTE bMajorRev;
  WORD wVariant;
  WORD ZZwDummy[22];
}
PCO_SC2_Firmware_DESC;

typedef struct
{
  WORD BoardNum;
  PCO_SC2_Hardware_DESC Board[10];
}
PCO_HW_Vers;

typedef struct
{
  WORD DeviceNum;
  PCO_SC2_Firmware_DESC Device[10];
}
PCO_FW_Vers;

typedef struct
{
  WORD wSize;
  WORD wCamType;
  WORD wCamSubType;
  WORD ZZwAlignDummy1;
  DWORD dwSerialNumber;
  DWORD dwHWVersion;
  DWORD dwFWVersion;
  WORD wInterfaceType;
  PCO_HW_Vers strHardwareVersion;
  PCO_FW_Vers strFirmwareVersion;
  WORD ZZwDummy[39];
} PCO_CameraType;

typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  PCO_CameraType strCamType;
  DWORD dwCamHealthWarnings;
  DWORD dwCamHealthErrors;
  DWORD dwCamHealthStatus;
  SHORT sCCDTemperature;
  SHORT sCamTemperature;
  SHORT sPowerSupplyTemperature;
  WORD ZZwDummy[37];
} PCO_General;

typedef struct
{
  WORD wSize;
  WORD wSensorTypeDESC;
  WORD wSensorSubTypeDESC;
  WORD wMaxHorzResStdDESC;
  WORD wMaxVertResStdDESC;
  WORD wMaxHorzResExtDESC;
  WORD wMaxVertResExtDESC;
  WORD wDynResDESC;
  WORD wMaxBinHorzDESC;
  WORD wBinHorzSteppingDESC;
  WORD wMaxBinVertDESC;
  WORD wBinVertSteppingDESC;
  WORD wRoiHorStepsDESC;
  WORD wRoiVertStepsDESC;
  WORD wNumADCsDESC;
  WORD wMinSizeHorzDESC;
  DWORD dwPixelRateDESC[4];
  DWORD ZZdwDummypr[20];
  WORD wConvFactDESC[4];
  SHORT sCoolingSetpoints[10];
  WORD ZZdwDummycv[8];
  WORD wSoftRoiHorStepsDESC;
  WORD wSoftRoiVertStepsDESC;
  WORD wIRDESC;
  WORD wMinSizeVertDESC;
  DWORD dwMinDelayDESC;
  DWORD dwMaxDelayDESC;
  DWORD dwMinDelayStepDESC;
  DWORD dwMinExposureDESC;
  DWORD dwMaxExposureDESC;
  DWORD dwMinExposureStepDESC;
  DWORD dwMinDelayIRDESC;
  DWORD dwMaxDelayIRDESC;
  DWORD dwMinExposureIRDESC;
  DWORD dwMaxExposureIRDESC;
  WORD wTimeTableDESC;
  WORD wDoubleImageDESC;
  SHORT sMinCoolSetDESC;
  SHORT sMaxCoolSetDESC;
  SHORT sDefaultCoolSetDESC;
  WORD wPowerDownModeDESC;
  WORD wOffsetRegulationDESC;
  WORD wColorPatternDESC;
# 310 "headers/sc2_SDKStructures.h"
  WORD wPatternTypeDESC;


  WORD wDummy1;
  WORD wDummy2;
  WORD wNumCoolingSetpoints;
  DWORD dwGeneralCapsDESC1;
# 350 "headers/sc2_SDKStructures.h"
  DWORD dwGeneralCapsDESC2;



  DWORD dwExtSyncFrequency[2];
  DWORD dwReservedDESC[4];
  DWORD ZZdwDummy[40];
} PCO_Description;

typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  DWORD dwMinPeriodicalTimeDESC2;
  DWORD dwMaxPeriodicalTimeDESC2;
  DWORD dwMinPeriodicalConditionDESC2;


  DWORD dwMaxNumberOfExposuresDESC2;
  LONG lMinMonitorSignalOffsetDESC2;




  DWORD dwMaxMonitorSignalOffsetDESC2;
  DWORD dwMinPeriodicalStepDESC2;
  DWORD dwStartTimeDelayDESC2;

  DWORD dwMinMonitorStepDESC2;
  DWORD dwMinDelayModDESC2;
  DWORD dwMaxDelayModDESC2;
  DWORD dwMinDelayStepModDESC2;
  DWORD dwMinExposureModDESC2;
  DWORD dwMaxExposureModDESC2;
  DWORD dwMinExposureStepModDESC2;
  DWORD dwModulateCapsDESC2;
  DWORD dwReserved[16];
  DWORD ZZdwDummy[41];
} PCO_Description2;

typedef struct
{
  WORD wSize;
} PCO_DescriptionEx;
# 402 "headers/sc2_SDKStructures.h"
typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  char strSignalName[4][25];

  WORD wSignalDefinitions;







  WORD wSignalTypes;





  WORD wSignalPolarity;






  WORD wSignalFilter;




  DWORD dwDummy[22];
}PCO_Single_Signal_Desc;

typedef struct
{
  WORD wSize;
  WORD wNumOfSignals;
  PCO_Single_Signal_Desc strSingeSignalDesc[20];
  DWORD dwDummy[524];
} PCO_Signal_Description;


typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  PCO_Description strDescription;
  PCO_Description2 strDescription2;
  DWORD ZZdwDummy2[256];
  WORD wSensorformat;
  WORD wRoiX0;
  WORD wRoiY0;
  WORD wRoiX1;
  WORD wRoiY1;
  WORD wBinHorz;
  WORD wBinVert;
  WORD ZZwAlignDummy2;
  DWORD dwPixelRate;

  WORD wConvFact;

  WORD wDoubleImage;
  WORD wADCOperation;
  WORD wIR;
  SHORT sCoolSet;
  WORD wOffsetRegulation;
  WORD wNoiseFilterMode;
  WORD wFastReadoutMode;
  WORD wDSNUAdjustMode;
  WORD wCDIMode;
  WORD ZZwDummy[36];
  PCO_Signal_Description strSignalDesc;
  DWORD ZZdwDummy[7];
} PCO_Sensor;

typedef struct
{
  WORD wSize;
  WORD wSignalNum;
  WORD wEnabled;
  WORD wType;
  WORD wPolarity;
  WORD wFilterSetting;
  WORD wSelected;
  WORD ZZwReserved;
  DWORD dwParameter[4];
  DWORD dwSignalFunctionality[4];

  DWORD ZZdwReserved[3];
} PCO_Signal;

typedef struct
{
  WORD wSize;
  WORD wDummy;
  DWORD FrameTime_ns;
  DWORD FrameTime_s;
  DWORD ExposureTime_ns;
  DWORD ExposureTime_s;
  DWORD TriggerSystemDelay_ns;
  DWORD TriggerSystemJitter_ns;
  DWORD TriggerDelay_ns;
  DWORD TriggerDelay_s;
  DWORD ZZdwDummy[11];
} PCO_ImageTiming;



typedef struct
{
  WORD wSize;
  WORD wTimeBaseDelay;
  WORD wTimeBaseExposure;
  WORD ZZwAlignDummy1;
  DWORD ZZdwDummy0[2];
  DWORD dwDelayTable[16];
  DWORD ZZdwDummy1[114];
  DWORD dwExposureTable[16];
  DWORD ZZdwDummy2[112];
  WORD wTriggerMode;

  WORD wForceTrigger;
  WORD wCameraBusyStatus;
  WORD wPowerDownMode;
  DWORD dwPowerDownTime;
  WORD wExpTrgSignal;
  WORD wFPSExposureMode;
  DWORD dwFPSExposureTime;

  WORD wModulationMode;
  WORD wCameraSynchMode;
  DWORD dwPeriodicalTime;
  WORD wTimeBasePeriodical;
  WORD ZZwAlignDummy3;
  DWORD dwNumberOfExposures;
  LONG lMonitorOffset;
  PCO_Signal strSignal[20];
  WORD wStatusFrameRate;
  WORD wFrameRateMode;
  DWORD dwFrameRate;
  DWORD dwFrameRateExposure;
  WORD wTimingControlMode;
  WORD wFastTimingMode;
  WORD ZZwDummy[24];
} PCO_Timing;


typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  DWORD dwRamSize;
  WORD wPageSize;
  WORD ZZwAlignDummy4;
  DWORD dwRamSegSize[4];
  DWORD ZZdwDummyrs[20];
  WORD wActSeg;
  WORD ZZwDummy[39];
} PCO_Storage;


typedef struct
{
  WORD wSize;
  WORD wStorageMode;
  WORD wRecSubmode;
  WORD wRecState;
  WORD wAcquMode;
  WORD wAcquEnableStatus;
  BYTE ucDay;
  BYTE ucMonth;
  WORD wYear;
  WORD wHour;
  BYTE ucMin;
  BYTE ucSec;
  WORD wTimeStampMode;
  WORD wRecordStopEventMode;
  DWORD dwRecordStopDelayImages;
  WORD wMetaDataMode;
  WORD wMetaDataSize;
  WORD wMetaDataVersion;
  WORD ZZwDummy1;
  DWORD dwAcquModeExNumberImages;
  DWORD dwAcquModeExReserved[4];
  WORD ZZwDummy[22];
} PCO_Recording;

typedef struct
{
  WORD wSize;
  WORD wXRes;
  WORD wYRes;
  WORD wBinHorz;
  WORD wBinVert;
  WORD wRoiX0;
  WORD wRoiY0;
  WORD wRoiX1;
  WORD wRoiY1;
  WORD ZZwAlignDummy1;
  DWORD dwValidImageCnt;
  DWORD dwMaxImageCnt;
  WORD wRoiSoftX0;
  WORD wRoiSoftY0;
  WORD wRoiSoftX1;
  WORD wRoiSoftY1;
  WORD wRoiSoftXRes;
  WORD wRoiSoftYRes;
  WORD wRoiSoftDouble;
  WORD ZZwDummy[33];
} PCO_Segment;

typedef struct
{
  WORD wSize;
  SHORT sSaturation;
  SHORT sVibrance;
  WORD wColorTemp;
  SHORT sTint;
  WORD wMulNormR;
  WORD wMulNormG;
  WORD wMulNormB;
  SHORT sContrast;
  WORD wGamma;
  WORD wSharpFixed;
  WORD wSharpAdaptive;
  WORD wScaleMin;
  WORD wScaleMax;
  WORD wProcOptions;
  WORD ZZwDummy[93];
} PCO_Image_ColorSet;

typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  PCO_Segment strSegment[4];


  PCO_Segment ZZstrDummySeg[14];
  PCO_Image_ColorSet strColorSet;
  WORD wBitAlignment;
  WORD wHotPixelCorrectionMode;
  WORD ZZwDummy[38];
} PCO_Image;
# 669 "headers/sc2_SDKStructures.h"
typedef struct
{
  WORD wSize;
  WORD ZZwAlignDummy1;
  DWORD dwBufferStatus;
  HANDLE hBufferEvent;

  DWORD ZZdwBufferAddress;
  DWORD dwBufferSize;
  DWORD dwDrvBufferStatus;
  DWORD dwImageSize;
  void *pBufferAdress;



  WORD ZZwDummy[32];
} PCO_APIBuffer;
# 697 "headers/sc2_SDKStructures.h"
typedef struct
{
  WORD wSize;
  WORD wCameraNum;
  HANDLE hCamera;
  WORD wTakenFlag;
  WORD wAPIManagementFlags;
  void *pSC2IFFunc[20];
  PCO_APIBuffer strPCOBuf[16];
  PCO_APIBuffer ZZstrDummyBuf[12];
  SHORT sBufferCnt;
  WORD wCameraNumAtInterface;
  WORD wInterface;

  WORD wXRes;
  WORD wYRes;
  WORD ZZwAlignDummy2;
  DWORD dwIF_param[5];





  WORD wImageTransferMode;
  WORD wRoiSoftX0;
  WORD wRoiSoftY0;
  WORD wRoiSoftX1;
  WORD wRoiSoftY1;
  WORD wImageTransferParam[2];
  WORD ZZwDummy[19];
} PCO_APIManagement;

typedef struct
{
  WORD wSize;
  WORD wStructRev;
  PCO_General strGeneral;
  PCO_Sensor strSensor;
  PCO_Timing strTiming;
  PCO_Storage strStorage;
  PCO_Recording strRecording;
  PCO_Image strImage;
  PCO_APIManagement strAPIManager;
  WORD ZZwDummy[40];
} PCO_Camera;
# 38 "test.h" 2
# 1 "headers/SC2_CamExport.h" 1
# 197 "headers/SC2_CamExport.h"
 int PCO_GetGeneral(HANDLE ph, PCO_General *strGeneral);
# 211 "headers/SC2_CamExport.h"
 int PCO_GetCameraType(HANDLE ph, PCO_CameraType *strCamType);
# 224 "headers/SC2_CamExport.h"
 int PCO_GetCameraHealthStatus(HANDLE ph, DWORD* dwWarn, DWORD* dwErr, DWORD* dwStatus);
# 240 "headers/SC2_CamExport.h"
 int PCO_ResetSettingsToDefault(HANDLE ph);





 int PCO_InitiateSelftestProcedure(HANDLE ph);





 int PCO_GetTemperature(HANDLE ph, SHORT* sCCDTemp, SHORT* sCamTemp, SHORT* sPowTemp);
# 261 "headers/SC2_CamExport.h"
 int PCO_GetInfoString(HANDLE ph, DWORD dwinfotype,
                         char *buf_in, WORD size_in);
# 272 "headers/SC2_CamExport.h"
 int PCO_GetCameraName(HANDLE ph, char* szCameraName, WORD wSZCameraNameLen);







 int PCO_GetFirmwareInfo(HANDLE ph, WORD wDeviceBlock, PCO_FW_Vers* pstrFirmWareVersion);







 int PCO_GetCameraSetup(HANDLE ph, WORD *wType, DWORD *dwSetup, WORD *wLen);
# 298 "headers/SC2_CamExport.h"
 int PCO_SetCameraSetup(HANDLE ph, WORD wType, DWORD *dwSetup, WORD wLen);
# 310 "headers/SC2_CamExport.h"
 int PCO_RebootCamera(HANDLE ph);




 int PCO_GetPowerSaveMode(HANDLE ph, WORD *wMode, WORD *wDelayMinutes);
# 325 "headers/SC2_CamExport.h"
 int PCO_SetPowerSaveMode(HANDLE ph, WORD wMode, WORD wDelayMinutes);
# 335 "headers/SC2_CamExport.h"
 int PCO_GetBatteryStatus(HANDLE ph, WORD *wBatteryType, WORD *wBatteryLevel,
                                             WORD *wPowerStatus, WORD *wReserved, WORD wNumReserved);
# 364 "headers/SC2_CamExport.h"
 int PCO_GetSensorStruct(HANDLE ph, PCO_Sensor *strSensor);






 int PCO_SetSensorStruct(HANDLE ph, PCO_Sensor *strSensor);
# 395 "headers/SC2_CamExport.h"
 int PCO_GetCameraDescription(HANDLE ph, PCO_Description *strDescription);






 int PCO_GetCameraDescriptionEx(HANDLE ph, PCO_DescriptionEx *strDescription, WORD wType);
# 411 "headers/SC2_CamExport.h"
 int PCO_GetSensorFormat(HANDLE ph, WORD* wSensor);
# 424 "headers/SC2_CamExport.h"
 int PCO_SetSensorFormat(HANDLE ph, WORD wSensor);
# 438 "headers/SC2_CamExport.h"
 int PCO_GetSizes(HANDLE ph,
                            WORD *wXResAct,
                            WORD *wYResAct,
                            WORD *wXResMax,
                            WORD *wYResMax);
# 462 "headers/SC2_CamExport.h"
 int PCO_GetROI(HANDLE ph,
                            WORD *wRoiX0,
                            WORD *wRoiY0,
                            WORD *wRoiX1,
                            WORD *wRoiY1);
# 479 "headers/SC2_CamExport.h"
 int PCO_SetROI(HANDLE ph,
                            WORD wRoiX0,
                            WORD wRoiY0,
                            WORD wRoiX1,
                            WORD wRoiY1);
# 507 "headers/SC2_CamExport.h"
 int PCO_GetBinning(HANDLE ph,
                                WORD *wBinHorz,
                                WORD *wBinVert);







 int PCO_SetBinning(HANDLE ph,
                                WORD wBinHorz,
                                WORD wBinVert);







 int PCO_GetPixelRate(HANDLE ph,
                                  DWORD *dwPixelRate);
# 542 "headers/SC2_CamExport.h"
 int PCO_SetPixelRate(HANDLE ph,
                                  DWORD dwPixelRate);
# 558 "headers/SC2_CamExport.h"
 int PCO_GetConversionFactor(HANDLE ph,
                                 WORD *wConvFact);





 int PCO_SetConversionFactor(HANDLE ph,
                                 WORD wConvFact);





 int PCO_GetDoubleImageMode(HANDLE ph,
                                        WORD *wDoubleImage);






 int PCO_SetDoubleImageMode(HANDLE ph,
                                        WORD wDoubleImage);






 int PCO_GetADCOperation(HANDLE ph,
                                     WORD *wADCOperation);





 int PCO_SetADCOperation(HANDLE ph,
                                     WORD wADCOperation);





 int PCO_GetIRSensitivity(HANDLE ph,
                               WORD *wIR);





 int PCO_SetIRSensitivity(HANDLE ph,
                               WORD wIR);





 int PCO_GetCoolingSetpoints(HANDLE ph, WORD wBlockID,
                                                WORD *wNumSetPoints,
                                                SHORT *sCoolSetpoints);
# 630 "headers/SC2_CamExport.h"
 int PCO_GetCoolingSetpointTemperature(HANDLE ph,
                                SHORT *sCoolSet);





 int PCO_SetCoolingSetpointTemperature(HANDLE ph,
                                SHORT sCoolSet);





 int PCO_GetOffsetMode(HANDLE ph,
                                   WORD *wOffsetRegulation);





 int PCO_SetOffsetMode(HANDLE ph,
                                   WORD wOffsetRegulation);





 int PCO_GetNoiseFilterMode(HANDLE ph,
                                   WORD *wNoiseFilterMode);





 int PCO_SetNoiseFilterMode(HANDLE ph,
                                   WORD wNoiseFilterMode);





 int PCO_GetHWIOSignalCount(HANDLE ph, WORD *wNumSignals);






 int PCO_GetHWIOSignalDescriptor(HANDLE ph, WORD wSignalNum, PCO_Single_Signal_Desc *pstrSignal);
# 688 "headers/SC2_CamExport.h"
 int PCO_GetColorCorrectionMatrix(HANDLE ph, double* pdMatrix);







 int PCO_GetBayerMultiplier(HANDLE ph, WORD *wMode, WORD *wMul);
# 711 "headers/SC2_CamExport.h"
 int PCO_SetBayerMultiplier(HANDLE ph, WORD wMode, WORD *wMul);
# 726 "headers/SC2_CamExport.h"
 int PCO_GetDSNUAdjustMode(HANDLE ph,
                                              WORD* wDSNUAdjustMode,
                                              WORD* wReserved);
# 737 "headers/SC2_CamExport.h"
 int PCO_SetDSNUAdjustMode(HANDLE ph,
                                              WORD wDSNUAdjustMode,
                                              WORD wReserved);
# 748 "headers/SC2_CamExport.h"
 int PCO_InitDSNUAdjustment(HANDLE ph,
                                               WORD wDSNUAdjustMode,
                                               WORD wReserved);
# 759 "headers/SC2_CamExport.h"
 int PCO_GetCDIMode(HANDLE ph,
                                       WORD *wCDIMode);






 int PCO_SetCDIMode(HANDLE ph,
                                       WORD wCDIMode);






 int PCO_GetLookupTableInfo(HANDLE ph,
  WORD wLUTNum,
  WORD *wNumberOfLuts,
  char *Description,
  WORD wDescLen,
  WORD *wIdentifier,
  BYTE *bInputWidth,
  BYTE *bOutputWidth,
  WORD *wFormat);






 int PCO_GetActiveLookupTable(HANDLE ph,
  WORD *wIdentifier,
  WORD *wParameter);






 int PCO_SetActiveLookupTable(HANDLE ph,
  WORD *wIdentifier,
  WORD *wParameter);






 int PCO_LoadLookupTable(HANDLE ph,
  WORD *wIdentifier,
  WORD *wPacketNum,
  WORD *wFormat,
  WORD *wLength,
  BYTE *bData);
# 827 "headers/SC2_CamExport.h"
 int PCO_GetTimingStruct(HANDLE ph, PCO_Timing *strTiming);





 int PCO_SetTimingStruct(HANDLE ph, PCO_Timing *strTiming);





 int PCO_GetDelayExposureTime(HANDLE ph,
                             DWORD* dwDelay,
                             DWORD* dwExposure,
                             WORD* wTimeBaseDelay,
                             WORD* wTimeBaseExposure);
# 855 "headers/SC2_CamExport.h"
 int PCO_SetDelayExposureTime(HANDLE ph,
                             DWORD dwDelay,
                             DWORD dwExposure,
                             WORD wTimeBaseDelay,
                             WORD wTimeBaseExposure);
# 868 "headers/SC2_CamExport.h"
 int PCO_GetDelayExposureTimeTable(HANDLE ph,
                                  DWORD* dwDelay,
                                  DWORD* dwExposure,
                                  WORD* wTimeBaseDelay,
                                  WORD* wTimeBaseExposure,
                                  WORD wCount);
# 883 "headers/SC2_CamExport.h"
 int PCO_SetDelayExposureTimeTable(HANDLE ph,
                                  DWORD* dwDelay,
                                  DWORD* dwExposure,
                                  WORD wTimeBaseDelay,
                                  WORD wTimeBaseExposure,
                                  WORD wCount);
# 913 "headers/SC2_CamExport.h"
 int PCO_GetTriggerMode(HANDLE ph, WORD* wTriggerMode);





 int PCO_SetTriggerMode(HANDLE ph, WORD wTriggerMode);





 int PCO_ForceTrigger(HANDLE ph, WORD *wTriggered);






 int PCO_GetCameraBusyStatus(HANDLE ph, WORD* wCameraBusyState);





 int PCO_GetPowerDownMode(HANDLE ph, WORD* wPowerDownMode);





 int PCO_SetPowerDownMode(HANDLE ph, WORD wPowerDownMode);





 int PCO_GetUserPowerDownTime(HANDLE ph, DWORD* dwPowerDownTime);





 int PCO_SetUserPowerDownTime(HANDLE ph, DWORD dwPowerDownTime);





 int PCO_GetExpTrigSignalStatus(HANDLE ph, WORD* wExpTrgSignal);






 int PCO_GetCOCRuntime(HANDLE ph, DWORD* dwTime_s, DWORD* dwTime_ns);
# 978 "headers/SC2_CamExport.h"
 int PCO_GetFPSExposureMode(HANDLE ph, WORD* wFPSExposureMode, DWORD* dwFPSExposureTime);







 int PCO_SetFPSExposureMode(HANDLE ph, WORD wFPSExposureMode, DWORD* dwFPSExposureTime);







 int PCO_GetModulationMode(HANDLE ph, WORD *wModulationMode, DWORD *dwPeriodicalTime,
                                              WORD *wTimebasePeriodical, DWORD *dwNumberOfExposures,
                                              LONG *lMonitorOffset);
# 1007 "headers/SC2_CamExport.h"
 int PCO_SetModulationMode(HANDLE ph, WORD wModulationMode, DWORD dwPeriodicalTime,
                                              WORD wTimebasePeriodical, DWORD dwNumberOfExposures,
                                              LONG lMonitorOffset);
# 1020 "headers/SC2_CamExport.h"
 int PCO_GetFrameRate(HANDLE ph, WORD* wFrameRateStatus, DWORD* dwFrameRate, DWORD* dwFrameRateExposure);
# 1033 "headers/SC2_CamExport.h"
 int PCO_SetFrameRate(HANDLE ph, WORD* wFrameRateStatus, WORD wFrameRateMode, DWORD* dwFrameRate, DWORD* dwFrameRateExposure);
# 1052 "headers/SC2_CamExport.h"
 int PCO_GetHWIOSignal(HANDLE ph, WORD wSignalNum, PCO_Signal *pstrSignal);







 int PCO_SetHWIOSignal(HANDLE ph, WORD wSignalNum, PCO_Signal *pstrSignal);







 int PCO_GetImageTiming(HANDLE ph, PCO_ImageTiming *pstrImageTiming);






 int PCO_GetCameraSynchMode(HANDLE ph, WORD *wCameraSynchMode);





 int PCO_SetCameraSynchMode(HANDLE ph, WORD wCameraSynchMode);





 int PCO_GetFastTimingMode(HANDLE hCam, WORD* wFastTimingMode);





 int PCO_SetFastTimingMode(HANDLE hCam, WORD wFastTimingMode);





 int PCO_GetSensorSignalStatus(HANDLE hCam, DWORD* dwStatus, DWORD* dwImageCount, DWORD* dwReserved1, DWORD *dwReserved2);
# 1114 "headers/SC2_CamExport.h"
 int PCO_GetHWLEDSignal(HANDLE hCam, DWORD* dwHWLEDSignal);
 int PCO_SetHWLEDSignal(HANDLE hCam, DWORD dwHWLEDSignal);
 int PCO_GetCmosLineTiming(HANDLE hCam, WORD* wParameter, WORD* wTimeBase,
                                              DWORD* dwLineTime, DWORD* dwReserved, WORD wReservedLen);


 int PCO_SetCmosLineTiming(HANDLE hCam, WORD wParameter, WORD wTimeBase,
                                              DWORD dwLineTime, DWORD* dwReserved, WORD wReservedLen);


 int PCO_GetCmosLineExposureDelay(HANDLE hCam, DWORD* dwExposureLines, DWORD* dwDelayLines,
                                                     DWORD* dwReserved, WORD wReservedLen);


 int PCO_SetCmosLineExposureDelay(HANDLE hCam, DWORD dwExposureLines, DWORD dwDelayLines,
                                                     DWORD* dwReserved, WORD wReservedLen);
# 1140 "headers/SC2_CamExport.h"
 int PCO_GetStorageStruct(HANDLE ph, PCO_Storage *strStorage);






 int PCO_SetStorageStruct(HANDLE ph, PCO_Storage *strStorage);






 int PCO_GetCameraRamSize(HANDLE ph, DWORD* dwRamSize, WORD* wPageSize);






 int PCO_GetCameraRamSegmentSize(HANDLE ph, DWORD* dwRamSegSize);






 int PCO_SetCameraRamSegmentSize(HANDLE ph, DWORD* dwRamSegSize);
# 1188 "headers/SC2_CamExport.h"
 int PCO_ClearRamSegment(HANDLE ph);




 int PCO_GetActiveRamSegment(HANDLE ph, WORD* wActSeg);





 int PCO_SetActiveRamSegment(HANDLE ph, WORD wActSeg);
# 1212 "headers/SC2_CamExport.h"
 int PCO_GetRecordingStruct(HANDLE ph, PCO_Recording *strRecording);





 int PCO_SetRecordingStruct(HANDLE ph, PCO_Recording *strRecording);





 int PCO_GetStorageMode(HANDLE ph, WORD* wStorageMode);





 int PCO_SetStorageMode(HANDLE ph, WORD wStorageMode);





 int PCO_GetRecorderSubmode(HANDLE ph, WORD* wRecSubmode);





 int PCO_SetRecorderSubmode(HANDLE ph, WORD wRecSubmode);





 int PCO_GetRecordingState(HANDLE ph, WORD* wRecState);





 int PCO_SetRecordingState(HANDLE ph, WORD wRecState);





 int PCO_ArmCamera(HANDLE ph);
# 1269 "headers/SC2_CamExport.h"
 int PCO_GetAcquireMode(HANDLE ph, WORD* wAcquMode);





 int PCO_SetAcquireMode(HANDLE ph, WORD wAcquMode);





 int PCO_GetAcquireModeEx(HANDLE ph, WORD* wAcquMode, DWORD* dwNumberImages, DWORD* dwReserved);







 int PCO_SetAcquireModeEx(HANDLE ph, WORD wAcquMode, DWORD dwNumberImages, DWORD* dwReserved);







 int PCO_GetAcqEnblSignalStatus(HANDLE ph, WORD* wAcquEnableState);






 int PCO_SetDateTime(HANDLE ph,
                                        BYTE ucDay,
                                        BYTE ucMonth,
                                        WORD wYear,
                                        WORD wHour,
                                        BYTE ucMin,
                                        BYTE ucSec);
# 1323 "headers/SC2_CamExport.h"
 int PCO_GetTimestampMode(HANDLE ph, WORD* wTimeStampMode);





 int PCO_SetTimestampMode(HANDLE ph, WORD wTimeStampMode);





 int PCO_GetRecordStopEvent(HANDLE ph, WORD* wRecordStopEventMode, DWORD *dwRecordStopDelayImages);







 int PCO_SetRecordStopEvent(HANDLE ph, WORD wRecordStopEventMode, DWORD dwRecordStopDelayImages);







 int PCO_StopRecord(HANDLE ph, WORD* wReserved0, DWORD *dwReserved1);
# 1368 "headers/SC2_CamExport.h"
 int PCO_GetImageStruct(HANDLE ph, PCO_Image *strImage);
# 1377 "headers/SC2_CamExport.h"
 int PCO_GetSegmentStruct(HANDLE ph, WORD wSegment, PCO_Segment *strSegment);







 int PCO_GetSegmentImageSettings(HANDLE ph, WORD wSegment,
                                                    WORD* wXRes,
                                                    WORD* wYRes,
                                                    WORD* wBinHorz,
                                                    WORD* wBinVert,
                                                    WORD* wRoiX0,
                                                    WORD* wRoiY0,
                                                    WORD* wRoiX1,
                                                    WORD* wRoiY1);
# 1412 "headers/SC2_CamExport.h"
 int PCO_GetNumberOfImagesInSegment(HANDLE ph,
                                             WORD wSegment,
                                             DWORD* dwValidImageCnt,
                                             DWORD* dwMaxImageCnt);






 int PCO_GetBitAlignment(HANDLE ph, WORD* wBitAlignment);





 int PCO_SetBitAlignment(HANDLE ph, WORD wBitAlignment);





 int PCO_WriteHotPixelList(HANDLE ph, WORD wListNo, WORD wNumValid,
                                 WORD* wHotPixX, WORD* wHotPixY);
# 1446 "headers/SC2_CamExport.h"
 int PCO_ReadHotPixelList(HANDLE ph, WORD wListNo, WORD wArraySize, WORD* wNumValid, WORD* wNumMax,
                                 WORD* wHotPixX, WORD* wHotPixY);
# 1465 "headers/SC2_CamExport.h"
 int PCO_ClearHotPixelList(HANDLE ph,
                                              WORD wListNo,
                                              DWORD dwMagic1,
                                              DWORD dwMagic2);






 int PCO_GetHotPixelCorrectionMode(HANDLE ph,
                                                      WORD *wHotPixelCorrectionMode);





 int PCO_SetHotPixelCorrectionMode(HANDLE ph,
                                                      WORD wHotPixelCorrectionMode);





 int PCO_PlayImagesFromSegmentHDSDI(HANDLE ph,
                                                       WORD wSegment,
                                                       WORD wInterface,
                                                       WORD wMode,
                                                       WORD wSpeed,
                                                       DWORD dwRangeLow,
                                                       DWORD dwRangeHigh,
                                                       DWORD dwStartPos);
# 1518 "headers/SC2_CamExport.h"
 int PCO_GetPlayPositionHDSDI(HANDLE ph,
                                                 WORD *wStatus,
                                                 DWORD *dwPlayPosition);
# 1529 "headers/SC2_CamExport.h"
 int PCO_GetInterfaceOutputFormat(HANDLE ph,
                                                     WORD *wDestInterface,
                                                     WORD *wFormat,
                                                     WORD *wReserved1,
                                                     WORD *wReserved2);
# 1548 "headers/SC2_CamExport.h"
 int PCO_SetInterfaceOutputFormat(HANDLE ph,
                                                     WORD wDestInterface,
                                                     WORD wFormat,
                                                     WORD wReserved1,
                                                     WORD wReserved2);
# 1567 "headers/SC2_CamExport.h"
 int PCO_GetMetaDataMode(HANDLE ph, WORD* wMetaDataMode, WORD* wMetaDataSize,
                                            WORD* wMetaDataVersion);
# 1577 "headers/SC2_CamExport.h"
 int PCO_SetMetaDataMode(HANDLE ph, WORD wMetaDataMode, WORD* wMetaDataSize,
                                            WORD* wMetaDataVersion);
# 1587 "headers/SC2_CamExport.h"
 int PCO_SetColorSettings(HANDLE ph, PCO_Image_ColorSet *strColorSet);






 int PCO_GetColorSettings(HANDLE ph, PCO_Image_ColorSet *strColorSet);






 int PCO_DoWhiteBalance(HANDLE ph, WORD wMode, WORD* wParam, WORD wParamLen);
# 1618 "headers/SC2_CamExport.h"
 int PCO_OpenCamera(HANDLE *ph, WORD wCamNum);
# 1631 "headers/SC2_CamExport.h"
 int PCO_OpenCameraEx(HANDLE *ph, PCO_OpenStruct* strOpenStruct);
# 1662 "headers/SC2_CamExport.h"
 int PCO_CloseCamera(HANDLE ph);
# 1674 "headers/SC2_CamExport.h"
 int PCO_AllocateBuffer(HANDLE ph,
                                           SHORT* sBufNr,
                                           DWORD size,
                                           WORD** wBuf,
                                           HANDLE *hEvent);
# 1717 "headers/SC2_CamExport.h"
 int PCO_WaitforBuffer(HANDLE ph, int nr_of_buffer, PCO_Buflist *bl, int timeout);
# 1726 "headers/SC2_CamExport.h"
 int PCO_GetBuffer(HANDLE ph, SHORT sBufNr, WORD** wBuf, HANDLE *hEvent);







 int PCO_FreeBuffer(HANDLE ph, SHORT sBufNr);





 int PCO_AddBuffer(HANDLE ph, DWORD dw1stImage, DWORD dwLastImage, SHORT sBufNr);
 int PCO_AddBufferEx(HANDLE ph, DWORD dw1stImage, DWORD dwLastImage, SHORT sBufNr,
                                        WORD wXRes, WORD wYRes, WORD wBitPerPixel);
# 1756 "headers/SC2_CamExport.h"
 int PCO_GetBufferStatus(HANDLE ph,
                                            SHORT sBufNr,
                                            DWORD *dwStatusDll,
                                            DWORD *dwStatusDrv);
# 1776 "headers/SC2_CamExport.h"
 int PCO_CancelImages(HANDLE ph);




 int PCO_RemoveBuffer(HANDLE ph);




 int PCO_GetImage(HANDLE ph, WORD wSegment, DWORD dw1stImage, DWORD dwLastImage, SHORT sBufNr);
 int PCO_GetImageEx(HANDLE ph, WORD wSegment, DWORD dw1stImage, DWORD dwLastImage, SHORT sBufNr,
                                        WORD wXRes, WORD wYRes, WORD wBitPerPixel);
# 1800 "headers/SC2_CamExport.h"
 int PCO_GetPendingBuffer(HANDLE ph, int *count);






 int PCO_CheckDeviceAvailability(HANDLE ph, WORD wNum);





 int PCO_SetTransferParameter(HANDLE ph, void* buffer, int ilen);






 int PCO_GetTransferParameter(HANDLE ph, void* buffer, int ilen);






 int PCO_SetTransferParametersAuto(HANDLE ph, void* buffer, int ilen);
# 1843 "headers/SC2_CamExport.h"
 int PCO_CamLinkSetImageParameters(HANDLE ph, WORD wxres, WORD wyres);
# 1856 "headers/SC2_CamExport.h"
 int PCO_SetImageParameters(HANDLE ph, WORD wxres, WORD wyres, DWORD dwflags, void* param, int ilen);
# 1874 "headers/SC2_CamExport.h"
 int PCO_SetTimeouts(HANDLE ph, void *buf_in,unsigned int size_in);
# 1884 "headers/SC2_CamExport.h"
 int PCO_GetGigEIPAddress(HANDLE ph,
                         BYTE *BField0, BYTE *BField1, BYTE *BField2, BYTE *BField3);
# 1895 "headers/SC2_CamExport.h"
 int PCO_SetGigEIPAddress(HANDLE ph, DWORD dwFlags,
                         BYTE BField0, BYTE BField1, BYTE BField2, BYTE BField3);
# 1907 "headers/SC2_CamExport.h"
 int PCO_GetImageTransferMode(HANDLE ph, void *param, int ilen);






 int PCO_SetImageTransferMode(HANDLE ph, void *param, int ilen);







 int PCO_AddBufferExtern(HANDLE ph, HANDLE hEvent, WORD wActSeg, DWORD dw1stImage,
                                            DWORD dwLastImage, DWORD dwSynch, void* pBuf, DWORD dwLen, DWORD *dwStatus);
# 1954 "headers/SC2_CamExport.h"
 int PCO_GetDeviceStatus(HANDLE ph, WORD wNum, DWORD *dwStatus, WORD wStatusLen);
# 1964 "headers/SC2_CamExport.h"
 int PCO_ControlCommandCall(HANDLE ph,
                         void *buf_in,unsigned int size_in,
                         void *buf_out,unsigned int size_out);






 int PCO_EnableInterface(WORD wInterface, WORD wInterfaceEnabled);



 int PCO_ResetLib();


 int PCO_EnableSoftROI(HANDLE ph, WORD wSoftROIFlags, void* , int );
# 1998 "headers/SC2_CamExport.h"
 int PCO_GetAPIManagement(HANDLE ph, WORD *wFlags, PCO_APIManagement* pstrApi);
# 2013 "headers/SC2_CamExport.h"
 int PCO_ReadHeadEEProm(HANDLE ph, WORD wAddress, BYTE* bData, WORD wLen);







 int PCO_WriteHeadEEProm(HANDLE ph, WORD wAddress, BYTE bData, WORD wLen);
# 2037 "headers/SC2_CamExport.h"
 int PCO_GetFlimModulationParameter(HANDLE ph,
                 WORD *wSourceSelect,
                 WORD *wOutputWaveform,
                 WORD *wReserved1,
                 WORD *wReserved2);







 int PCO_SetFlimModulationParameter(HANDLE ph,
                 WORD wSourceSelect,
                 WORD wOutputWaveform,
                 WORD wReserved1,
                 WORD wReserved2);







 int PCO_GetFlimPhaseSequenceParameter(HANDLE ph,
                 WORD *wPhaseNumber,
                 WORD *wPhaseSymmetry,
                 WORD *wPhaseOrder,
                 WORD *wTapSelect,
                 WORD *wReserved1,
                 WORD *wReserved2);
# 2077 "headers/SC2_CamExport.h"
 int PCO_SetFlimPhaseSequenceParameter(HANDLE ph,
                  WORD wPhaseNumber,
                  WORD wPhaseSymmetry,
                  WORD wPhaseOrder,
                  WORD wTapSelect,
                  WORD wReserved1,
                  WORD wReserved2);
# 2093 "headers/SC2_CamExport.h"
 int PCO_GetFlimImageProcessingFlow(HANDLE ph,
            WORD* wAsymmetryCorrection,
            WORD* wCalculationMode,
            WORD* wReferencingMode,
            WORD* wThresholdLow,
            WORD* wThresholdHigh,
            WORD* wOutputMode,
            WORD* wReserved1,
            WORD* wReserved2,
            WORD* wReserved3,
            WORD* wReserved4);
# 2114 "headers/SC2_CamExport.h"
 int PCO_SetFlimImageProcessingFlow(HANDLE ph,
             WORD wAsymmetryCorrection,
             WORD wCalculationMode,
             WORD wReferencingMode,
             WORD wThresholdLow,
             WORD wThresholdHigh,
             WORD wOutputMode,
             WORD wReserved1,
             WORD wReserved2,
             WORD wReserved3,
             WORD wReserved4);
# 2135 "headers/SC2_CamExport.h"
 int PCO_GetFlimMasterModulationFrequency(HANDLE ph,
                  DWORD *dwFrequency);





 int PCO_SetFlimMasterModulationFrequency(HANDLE ph,
                  DWORD dwFrequency);






 int PCO_GetFlimRelativePhase(HANDLE ph,
              DWORD *dwPhaseMilliDeg);





 int PCO_SetFlimRelativePhase(HANDLE ph,
               DWORD dwPhaseMilliDeg);
# 39 "test.h" 2
// A collection of #defines that skip the C preprocessor to be sent directly to cffi


// From "sc2_cl.h"
//timeout values in ms
typedef struct _PCO_SC2_TIMEOUTS {
   unsigned int command;
   unsigned int image;
   unsigned int transfer;
}PCO_SC2_TIMEOUTS;

typedef struct _PCO_SC2_CL_TRANSFER_PARAM_I {
   unsigned int   baudrate;              //serial baudrate
   unsigned int   ClockFrequency;        // Pixelclock in Hz
   unsigned int   CCline;                // Usage of CameraLink CC1-CC4 lines
   unsigned int   DataFormat;            // register with Testpattern and Datasplitter switch
   unsigned int   Transmit;              // single or continuous transmitting images
}PCO_SC2_CL_TRANSFER_PARAM_I;


typedef struct _PCO_SC2_CL_IMAGE_PARAM {
   unsigned int width;
   unsigned int height;
   unsigned int xoff;
   unsigned int yoff;
}PCO_SC2_CL_IMAGE_PARAM;


//default values
#define PCO_SC2_DEF_BLOCK_SIZE 512
#define PCO_SC2_MIN_COMMAND_SIZE 5

#define PCO_SC2_COMMAND_TIMEOUT 200
#define PCO_SC2_IMAGE_TIMEOUT   1500
#define PCO_SC2_IMAGE_TIMEOUT_L 3000

#define PCO_SC2_EVENT_ENABLE           0x80000000
#define PCO_SC2_POWER_DOWN_EV          0x00000001
#define PCO_SC2_CAMERA_ERROR_EV        0x00000002
#define PCO_SC2_IMAGE_READY_EV         0x00000004

/*
#define PCO_SC2_CL_DATAFORMAT  0x0F
#define PCO_SC2_CL_FORMAT_1x16 0x01
#define PCO_SC2_CL_FORMAT_2x12 0x02
#define PCO_SC2_CL_FORMAT_3x8  0x03
#define PCO_SC2_CL_FORMAT_4x16 0x04
#define PCO_SC2_CL_FORMAT_5x16 0x05
*/

#define CL_GRABBER_CAP_FORMAT_BASE       0x00000007
#define CL_GRABBER_CAP_FORMAT_1x16       0x00000001
#define CL_GRABBER_CAP_FORMAT_2x12       0x00000002
#define CL_GRABBER_CAP_FORMAT_3x8        0x00000004

#define CL_GRABBER_CAP_FORMAT_4x16       0x00000010
#define CL_GRABBER_CAP_FORMAT_5x16       0x00000020
#define CL_GRABBER_CAP_FORMAT_5x12       0x00000040

#define CL_GRABBER_CAP_SCCMOS_FORMAT_MODE_AD 0x000F0000
#define CL_GRABBER_CAP_SCCMOS_FORMAT_MODE_A  0x00010000
#define CL_GRABBER_CAP_SCCMOS_FORMAT_MODE_B  0x00020000
#define CL_GRABBER_CAP_SCCMOS_FORMAT_MODE_C  0x00040000
#define CL_GRABBER_CAP_SCCMOS_FORMAT_MODE_D  0x00080000


#define PCO_SC2_CL_TESTPATTERN 0x10

#define PCO_SC2_CL_NUMBER_OF_BUFFERS 3

#define NUMEVENTS 5
#define PCO_SC2_DRIVER_ENTRY_SIZE 10
//Maximum wait entries is set to 64 in winnt.h
#define PCO_SC2_WAIT_ENTRY_OV_SIZE 50
#define PCO_SC2_BUFFER_ENTRY_SIZE 30


#define PCO_SC2_CL_ALL_AQUIRE           0x003F
//
#define PCO_SC2_CL_START_CONT           0x0001
#define PCO_SC2_CL_NON_BLOCKING_BUFFER  0x0002
#define PCO_SC2_CL_BLOCKING_BUFFER      0x0004

#define PCO_SC2_CL_STARTED              0x0010
#define PCO_SC2_CL_START_INTERNAL       0x0020
#define PCO_SC2_CL_START_PENDING        0x0040
#define PCO_SC2_CL_STOP_PENDING         0x0080

#define PCO_SC2_CL_TRANSMIT_FLAGS       0x0F00

#define PCO_SC2_CL_TRANSMIT_SET         0x0100
#define PCO_SC2_CL_TRANSMIT_DISABLED    0x0200
#define PCO_SC2_CL_TRANSMIT_CHANGE      0x0400
#define PCO_SC2_CL_TRANSMIT_WAS_SET     0x0800

//buf_manager flag
#define PCO_SC2_CL_START_ALLOCATED      0x0001
#define PCO_SC2_CL_EXTERNAL_BUFFER      0x0002
#define PCO_SC2_CL_INTERNAL_BUFFER      0x0004
#define PCO_SC2_CL_ONLY_BUFFER_HEAD     0x0008
#define PCO_SC2_CL_NO_CONTEXT           0x0010
#define PCO_SC2_CL_NO_BUFFER_HEAD       0x0020


//initmode
#define PCO_SC2_CL_ME3_LOAD_APPLET      0x0F00

#define PCO_SC2_CL_ME3_LOAD_SINGLE_AREA 0x0100
#define PCO_SC2_CL_ME3_LOAD_DUAL_AREA   0x0200
#define PCO_SC2_CL_ME3_LOAD_SINGLE_LINE 0x0300
#define PCO_SC2_CL_ME3_LOAD_DUAL_LINE   0x0400

#define PCO_SC2_CL_ME4_LOAD_FULL_AREA   0x0500
#define PCO_SC2_CL_ME4_LOAD_PCO02_HAP   0x0600
#define PCO_SC2_CL_ME4_LOAD_PCO03_HAP   0x0700



#define PCO_SC2_CL_ME4_PCO_APP_TAP8     0
#define PCO_SC2_CL_ME4_PCO_APP_TAP10    1




#define PCO_SC2_CL_CCLINES_USAGE_MASK    0x000000FF
#define PCO_SC2_CL_CCLINES_SETTING_MASK  0xFFFF0000
#define PCO_SC2_CL_CCLINE1_SETTING_MASK  0x000F0000
#define PCO_SC2_CL_CCLINE1_SETTING_OFF   16
#define PCO_SC2_CL_CCLINE2_SETTING_MASK  0x00F00000
#define PCO_SC2_CL_CCLINE2_SETTING_OFF   20
#define PCO_SC2_CL_CCLINE3_SETTING_MASK  0x0F000000
#define PCO_SC2_CL_CCLINE3_SETTING_OFF   24
#define PCO_SC2_CL_CCLINE4_SETTING_MASK  0xF0000000
#define PCO_SC2_CL_CCLINE4_SETTING_OFF   28

enum PCO_CCsel {PCO_CC_EXSYNC,PCO_CC_NOT_EXSYNC,PCO_CC_HDSYNC,PCO_CC_NOT_HDSYNC,
                PCO_CC_STROBEPULSE,PCO_CC_NOT_STROBEPULSE,PCO_CC_CLK,
                PCO_CC_GND,PCO_CC_VCC};


//defines for synch

//GET_IMAGE_QUEUED
#define PCO_SC2_CL_SYNCH_SINGLE    0x0001 //synchronous input with seriell commands
#define PCO_SC2_CL_SYNCH_CONTI     0x0002 //driver set Transmit enable

//synch=0x10 read_image or request_image was already sent
//synch=0x20 image is marked as cancelled

//SET_IMAGE_BUFFER
#define PCO_SC2_CL_SYNCH_SENT      0x0010 //read_image or request_image was already sent
#define PCO_SC2_CL_SYNCH_CANCEL    0x0020 //image is marked as cancelled

//for test only
#define PCO_SC2_CL_SYNCH_CCLINE0   0x0100 //pulse line 0 trigger
#define PCO_SC2_CL_SYNCH_CCLINE3   0x0800 //pulse line 3 transmit

// Defines: 
// WORD: 16bit unsigned
// SHORT: 16bit signed
// DWORD: 32bit unsigned

#define PCO_STRUCTREV      102         // set this value to wStructRev

#define PCO_BUFCNT 16                   // see PCO_API struct
#define PCO_MAXDELEXPTABLE 16          // see PCO_Timing struct
#define PCO_RAMSEGCNT 4                // see PCO_Storage struct
#define PCO_MAXVERSIONHW   10
#define PCO_MAXVERSIONFW   10


#define PCO_ARM_COMMAND_TIMEOUT 10000
#define PCO_HPX_COMMAND_TIMEOUT 10000
#define PCO_COMMAND_TIMEOUT       400

// SDK-Dll internal defines (different to interface type in sc2_defs.h!!!
// In case you're going to enumerate interface types, please refer to sc2_defs.h.
#define PCO_INTERFACE_FW     1         // Firewire interface
#define PCO_INTERFACE_CL_MTX 2         // Cameralink Matrox Solios / Helios
#define PCO_INTERFACE_CL_ME3 3         // Cameralink Silicon Software Me3
#define PCO_INTERFACE_CL_NAT 4         // Cameralink National Instruments
#define PCO_INTERFACE_GIGE   5         // Gigabit Ethernet
#define PCO_INTERFACE_USB    6         // USB 2.0
#define PCO_INTERFACE_CL_ME4 7         // Cameralink Silicon Software Me4
#define PCO_INTERFACE_USB3   8         // USB 3.0
#define PCO_INTERFACE_WLAN   9         // WLan (Only control path, not data path)
#define PCO_INTERFACE_HS_ME5 11        // Cameralink HS sc2_hs_me5

#define PCO_LASTINTERFACE 11

#define PCO_INTERFACE_CL_SER 10
#define PCO_INTERFACE_GENERIC 20

#define PCO_OPENFLAG_GENERIC_IS_CAMLINK  0x0001 // In case a generic Camerlink interface is used (serial port)
                                       // set this flag (not necessary in automatic scanning)
#define PCO_OPENFLAG_HIDE_PROGRESS       0x0002 // Hides the progress dialog when automatic scanning runs



//-----------------------------------------------------------------//
// Name        | SC2_SDKAddendum.h           | Type: ( ) source    //
//-------------------------------------------|       (*) header    //
// Project     | PCO                         |       ( ) others    //
//-----------------------------------------------------------------//
// Platform    | PC                                                //
//-----------------------------------------------------------------//
// Environment | Visual 'C++'                                      //
//-----------------------------------------------------------------//
// Purpose     | PCO - SC2 Camera DLL Functions                    //
//-----------------------------------------------------------------//
// Author      | MBL, PCO AG                                       //
//-----------------------------------------------------------------//
// Revision    |  rev. 1.06 rel. 1.06                              //
//-----------------------------------------------------------------//

//-----------------------------------------------------------------//
// Notes       |                                                   //
//-----------------------------------------------------------------//
// (c) 2002 PCO AG * Donaupark 11 *                                //
// D-93309      Kelheim / Germany * Phone: +49 (0)9441 / 2005-0 *  //
// Fax: +49 (0)9441 / 2005-20 * Email: info@pco.de                 //
//-----------------------------------------------------------------//


//-----------------------------------------------------------------//
// Revision History:                                               //
//-----------------------------------------------------------------//
// Rev.:     | Date:      | Changed:                               //
// --------- | ---------- | ---------------------------------------//
//  1.02     | 04.05.2004 | new file added to SDK, FRE, MBL        //
//           |            |                                        //
//-----------------------------------------------------------------//
//  1.04     | 16.06.2005 | some defines MBL                       //
//           |            |                                        //
//-----------------------------------------------------------------//
//  1.05     | 27.02.2006 |  Added PCO_GetCameraName, FRE          //
//-----------------------------------------------------------------//
//  1.06     | 29.09.2008 |  Added PCO_GIGE_TRANSFER_PARAM, FRE    //
//-----------------------------------------------------------------//
//  1.07     | 23.11.2011 |  Added IMAGE_TRANSFER_MODE_PARAM, VTI  //
//-----------------------------------------------------------------//

typedef struct _PCO1394_ISO_PARAMS
{
   DWORD bandwidth_bytes;         // number of byte to allocate on the bus for isochronous transfers
                                  // 0...4096; recommended: 2048 (default 4096)
   DWORD speed_of_isotransfer;    // speed to use when allocating bandwidth
                                  // 1,2,4; recommended: 4 (default 4)
   DWORD number_of_isochannel;    // number of channel to use on the bus
                                  // 0...7 + additional bits (default AUTO_CHANNEL)
   DWORD number_of_iso_buffers;   // number of buffers to use when allocating transfer resources
                                  // depends on image size, auto adjusted from the driver
                                  // 16...256; recommended: 32 (default 32)
   DWORD byte_per_isoframe;       // 0...4096; information only
}PCO1394_ISO_PARAM;

#define PCO_1394_AUTO_CHANNEL   0x200
#define PCO_1394_HOLD_CHANNEL   0x100

#define PCO_1394_DEFAULT_BANDWIDTH 4096
#define PCO_1394_DEFAULT_SPEED 4
#define PCO_1394_DEFAULT_CHANNEL 0x00
#define PCO_1394_DEFAULT_ISOBUFFER 32

typedef struct _PCO_1394_TRANSFER_PARAM
{
   PCO1394_ISO_PARAM iso_param;
   DWORD bytes_avaiable;       //bytes avaiable on the bus 
   DWORD dummy[15];            //for future use, set to zero
}PCO_1394_TRANSFER_PARAM;


typedef struct _PCO_SC2_CL_TRANSFER_PARAMS
{
   DWORD   baudrate;         // serial baudrate: 9600, 19200, 38400, 56400, 115200
   DWORD   ClockFrequency;   // Pixelclock in Hz: 40000000,66000000,80000000
   DWORD   CCline;           // Usage of CameraLink CC1-CC4 lines, use value returned by Get 
   DWORD   DataFormat;       // see defines below, use value returned by Get
   DWORD   Transmit;         // single or continuous transmitting images, 0-single, 1-continuous
}PCO_SC2_CL_TRANSFER_PARAM;

#define PCO_CL_DEFAULT_BAUDRATE 9600
#define PCO_CL_PIXELCLOCK_40MHZ 40000000
#define PCO_CL_PIXELCLOCK_66MHZ 66000000
#define PCO_CL_PIXELCLOCK_80MHZ 80000000
#define PCO_CL_PIXELCLOCK_32MHZ 32000000
#define PCO_CL_PIXELCLOCK_64MHZ 64000000

#define PCO_CL_CCLINE_LINE1_TRIGGER           0x01
#define PCO_CL_CCLINE_LINE2_ACQUIRE           0x02
#define PCO_CL_CCLINE_LINE3_HANDSHAKE         0x04
#define PCO_CL_CCLINE_LINE4_TRANSMIT_ENABLE   0x08

#define PCO_CL_DATAFORMAT_MASK   0x0F
#define PCO_CL_DATAFORMAT_1x16   0x01
#define PCO_CL_DATAFORMAT_2x12   0x02
#define PCO_CL_DATAFORMAT_3x8    0x03
#define PCO_CL_DATAFORMAT_4x16   0x04
#define PCO_CL_DATAFORMAT_5x16   0x05
#define PCO_CL_DATAFORMAT_5x12   0x07     //extract data to 12bit
#define PCO_CL_DATAFORMAT_10x8   0x08
#define PCO_CL_DATAFORMAT_5x12L  0x09     //extract data to 16Bit
#define PCO_CL_DATAFORMAT_5x12R  0x0A     //without extract


#define SCCMOS_FORMAT_MASK                                        0xFF00
#define SCCMOS_FORMAT_TOP_BOTTOM                                  0x0000  //Mode E 
#define SCCMOS_FORMAT_TOP_CENTER_BOTTOM_CENTER                    0x0100  //Mode A
#define SCCMOS_FORMAT_CENTER_TOP_CENTER_BOTTOM                    0x0200  //Mode B
#define SCCMOS_FORMAT_CENTER_TOP_BOTTOM_CENTER                    0x0300  //Mode C
#define SCCMOS_FORMAT_TOP_CENTER_CENTER_BOTTOM                    0x0400  //Mode D 

#define PCO_CL_TRANSMIT_ENABLE  0x01
#define PCO_CL_TRANSMIT_LONGGAP 0x02


typedef struct _PCO_USB_TRANSFER_PARAM {
   unsigned int   MaxNumUsb;           // defines packet size 
   unsigned int   ClockFrequency;      // Pixelclock in Hz: 40000000,66000000,80000000
   unsigned int   Transmit;            // single or continuous transmitting images, 0-single, 1-continuous
   unsigned int   UsbConfig;           // 0=bulk_image, 1=iso_image
   unsigned int   Img12Bit;			   // 1: 12Bit Image 0: 14Bit Image
}PCO_USB_TRANSFER_PARAM;

#define PCO_GIGE_PAKET_RESEND    0x00000001
#define PCO_GIGE_BURST_MODE      0x00000002
#define PCO_GIGE_MAXSPEED_MODE   0x00000004
#define PCO_GIGE_DEBUG_MODE		 0x00000008
#define PCO_GIGE_BW_SAME2ALL	 0x00000000
#define PCO_GIGE_BW_ALL2MAX		 0x00000010
#define PCO_GIGE_BW_2ACTIVE		 0x00000020
#define PCO_GIGE_DATAFORMAT_1x8  0x01080001
#define PCO_GIGE_DATAFORMAT_1x16 0x01100007
#define PCO_GIGE_DATAFORMAT_3x8  0x02180015
#define PCO_GIGE_DATAFORMAT_4x8  0x02200016

typedef struct _PCO_GIGE_TRANSFER_PARAM
{
  DWORD dwPacketDelay;                 // delay between image stream packets (number of clockticks of a 100MHz clock;
                                       // default: 2000 -> 20us, range: 0 ... 8000 -> 0 ... 80us)
  DWORD dwResendPercent;               // Number of lost packets of image in percent. If more packets got lost,
                                       // complete image will be resent or image transfer is failed (default 30).
  DWORD dwFlags;                       // Bit 0:   Set to enable packet resend
                                       // Bit 1:   Set to enable Burst_mode
									   // Bit 2:   Set to enable Max Speed Modus
									   // Bit 3:   Set to enable Camera Debug Mode
									   // Bit 4-7:   Reserved
								       // Bit 8-11:0: Bandwidth is devided by number of connected cameras. PCO_GIGE_BW_SAME2ALL
									   //	       1: Max-Speed-Mode is allways active regardless how many cameras are connected. PCO_GIGE_BW_ALL2MAX
									   //          2: Maximal possible Bandwidth is used for active camera. Just one active camera is allowed. PCO_GIGE_BW_2ACTIVE
									   // Bit 12-31: Reserved
                                       // (LSB; default 0x00000001).      
  DWORD dwDataFormat;                  // DataFormat: default:  0x01100007
                                       // supported types:  Mono, 8Bit:  0x01080001
                                       //                   Mono, 16Bit: 0x01100007
                                       //                   RGB,  24Bit: 0x02180015  (R=G=B=8Bit)
                                       //                   RGB,  32Bit: 0x02200016  (R=G=B=a=8Bit)
  DWORD dwCameraIPAddress;             // Current Ip Address of the Camera
									   //  (can not be changed with Set_Transfer_Param() routine )
  DWORD dwUDPImgPcktSize;			   // Size of an UDP Image packet
									   //  (can not be changed with Set_Transfer_Param() routine )
  UINT64 ui64MACAddress;               // Settings are attached to this interface

}PCO_GIGE_TRANSFER_PARAM; 


typedef struct _IMAGE_TRANSFER_MODE_PARAM
{
  WORD        wSize;               // size of this struct
  WORD        wMode;               // transfer mode, e.g. full, scaled, cutout etc.
  WORD        wImageWidth;         // original image width
  WORD        wImageHeight;        // original image height
  WORD        wTxWidth;            // width of transferred image (scaled or cutout)
  WORD        wTxHeight;           // width of transferred image (scaled or cutout)
  WORD        wParam[8];           // params, meaning depends on selected mode else set to zero
  WORD        ZZwDummy[10];        // for future use, set to zero
} IMAGE_TRANSFER_MODE_PARAM;


//loglevels for interface dll
#define ERROR_M     0x0001
#define INIT_M      0x0002
#define BUFFER_M    0x0004
#define PROCESS_M   0x0008

#define COC_M       0x0010
#define INFO_M      0x0020
#define COMMAND_M   0x0040

#define PCI_M       0x0020

#define TIME_M      0x1000 
#define TIME_MD     0x2000 
#define THREAD_ID   0x4000 
#define CPU_ID      0x8000           // not on XP
