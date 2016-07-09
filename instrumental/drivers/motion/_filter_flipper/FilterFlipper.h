	typedef enum 
	{
		FT_OK = 0x00, /// <OK - no error.
		FT_InvalidHandle = 0x01, ///<Invalid handle.
		FT_DeviceNotFound = 0x02, ///<Device not found.
		FT_DeviceNotOpened = 0x03, ///<Device not opened.
		FT_IOError = 0x04, ///<I/O error.
		FT_InsufficientResources = 0x05, ///<Insufficient resources.
		FT_InvalidParameter = 0x06, ///<Invalid parameter.
		FT_DeviceNotPresent = 0x07, ///<Device not present.
		FT_IncorrectDevice = 0x08 ///<Incorrect device.
	 } FT_Status;

	typedef enum 
	{
		MOT_NotMotor = 0,
		MOT_DCMotor = 1,
		MOT_StepperMotor = 2,
		MOT_BrushlessMotor = 3,
		MOT_CustomMotor = 100,
	} MOT_MotorTypes;


	/// <summary> Values that represent the two filter flipper positions. </summary>
	typedef enum 
	{
		FF_PositionError=0,///<Position error
		Position1 = 0x01,///<Position 1
		Position2 = 0x02,///<Position 2
	} FF_Positions;

	/// \endcond

	/// <summary> Information about the device generated from serial number. </summary>
	#pragma pack(1)
	typedef struct 
	{
		/// <summary> The device Type ID, see \ref C_DEVICEID_page "Device serial numbers". </summary>
		DWORD typeID;
		/// <summary> The device description. </summary>
		char description[65];
		/// <summary> The device serial number. </summary>
		char serialNo[9];
		/// <summary> The USB PID number. </summary>
		DWORD PID;

		/// <summary> <c>true</c> if this object is a type known to the Motion Control software. </summary>
		bool isKnownType;
		/// <summary> The motor type (if a motor).
		/// 		  <list type=table>
		///				<item><term>MOT_NotMotor</term><term>0</term></item>
		///				<item><term>MOT_DCMotor</term><term>1</term></item>
		///				<item><term>MOT_StepperMotor</term><term>2</term></item>
		///				<item><term>MOT_BrushlessMotor</term><term>3</term></item>
		///				<item><term>MOT_CustomMotor</term><term>100</term></item>
		/// 		  </list> </summary>
		MOT_MotorTypes motorType;

		/// <summary> <c>true</c> if the device is a piezo device. </summary>
		bool isPiezoDevice;
		/// <summary> <c>true</c> if the device is a laser. </summary>
		bool isLaser;
		/// <summary> <c>true</c> if the device is a custom type. </summary>
		bool isCustomType;
		/// <summary> <c>true</c> if the device is a rack. </summary>
		bool isRack;
		/// <summary> Defines the number of channels available in this device. </summary>
		short maxChannels;
	} TLI_DeviceInfo;

	/// <summary> Structure containing the Hardware Information. </summary>
	/// <value> Hardware Information retrieved from tthe device. </value>
	typedef struct 
	{
		/// <summary> The device serial number. </summary>
		/// <remarks> The device serial number is a serial number,<br />starting with 2 digits representing the device type<br /> and a 6 digit unique value.</remarks>
		DWORD serialNumber;
		/// <summary> The device model number. </summary>
		/// <remarks> The model number uniquely identifies the device type as a string. </remarks>
		char modelNumber[8];
		/// <summary> The device type. </summary>
		/// <remarks> Each device type has a unique Type ID: see \ref C_DEVICEID_page "Device serial numbers" </remarks>
		WORD type;
		/// <summary> The number of channels the device provides. </summary>
		short numChannels;
		/// <summary> The device notes read from the device. </summary>
		char notes[48];
		/// <summary> The device firmware version. </summary>
		DWORD firmwareVersion;
		/// <summary> The device hardware version. </summary>
		WORD hardwareVersion;
		/// <summary> The device dependant data. </summary>
		BYTE deviceDependantData[12];
		/// <summary> The device modification state. </summary>
		WORD modificationState;
	} TLI_HardwareInformation;

	/// <summary> FilterFlipper IO operations. </summary>
	typedef enum 
	{
		/// <summary> Input Mode - FilterFlipper toggles when signalled (See <see cref="FF_SignalModes" />). </summary>
		FF_ToggleOnPositiveEdge = 0x01, 
		/// <summary> Input Mode - FilterFlipper goes to position when signalled (See <see cref="FF_SignalModes" />) </summary>
		FF_SetPositionOnPositiveEdge = 0x02, 
		/// <summary> Output Mode - Output signal set to match position, where 2 = Hi, 1 = Lo. </summary>
		FF_OutputHighAtSetPosition = 0x04, 
		/// <summary> Output Mode - Output signal high when FilterFlipper is moving. </summary>
		FF_OutputHighWhemMoving = 0x08, 
	} FF_IOModes;

	/// <summary> FilterFlipper IO operations. </summary>
	typedef enum 
	{
		/// <summary> Signal is raised when Button Pressed i.e. Hi to Lo. Action taken is defined by <see cref="FF_IOModes" />. </summary>
		FF_InputButton = 0x01, 
		/// <summary> Signal is raised on on rising edge Lo to Hi. Action taken is defined by <see cref="FF_IOModes" />. </summary>
		FF_InputLogic = 0x02, 
		/// <summary> when set will swap Position 1 and 2. </summary>
		FF_InputSwap = 0x04, 
		/// <summary> Output is set to either be hi when flipper at Position 2 or flipper is moving (see <see cref="FF_IOModes" />). </summary>
		FF_OutputLevel = 0x10, 
		/// <summary> Output is set to pulse when flipper operates, either when flipper reaches Position or flipper starts moving (see <see cref="FF_IOModes" />). </summary>
		FF_OutputPulse = 0x20, 
		/// <summary> when set will swap output logic levels. </summary>
		FF_OutputSwap = 0x40, 
	} FF_SignalModes;

	/// <summary> Structure containing settings specific to filter flipper input / output. </summary>
	typedef struct 
	{
		/// <summary> Time taken to get from one position to other in milliseconds.<br />
		/// 		  Range 300 to 2800 ms. </summary>
		unsigned int transitTime;
		/// <summary> Value derived from transition time in ADC units. </summary>
		unsigned int ADCspeedValue;
		/// <summary> I/O 1 Operating Mode
		/// 		  <list type=table>
		///				<item><term>Input Mode - FilterFlipper toggles when signalled (See <see cref="FF_SignalModes" />)</term><term>0x01</term></item>
		///				<item><term>Input Mode - FilterFlipper goes to position when signalled (See <see cref="FF_SignalModes" />)</term><term>0x02</term></item>
		///				<item><term>Output Mode - Output signal set to match position, where 2 = Hi, 1 = Lo</term><term>0x04</term></item>
		///				<item><term>Output Mode - Output signal high when FilterFlipper is moving</term><term>0x08</term></item>
		/// 		  </list> </summary>
		FF_IOModes digIO1OperMode;
		/// <summary> I/O 1 Signal Mode
		/// 		  <list type=table>
		///				<item><term>Signal is raised when Button Pressed i.e. Hi to Lo. Action taken is defined by <see cref="FF_IOModes" /></term><term>0x01</term></item>
		///				<item><term>Signal is raised on on rising edge Lo to Hi. Action taken is defined by <see cref="FF_IOModes" /></term><term>0x02</term></item>
		///				<item><term>Toggle Positions, when set will swap Position 1 and 2</term><term>0x04</term></item>
		///				<item><term>Output is set to either be hi when flipper at Position 2 or flipper is moving (see <see cref="FF_IOModes" />)</term><term>0x10</term></item>
		///				<item><term>Output is set to pulse when flipper operates, either when flipper reaches Position or flipper starts moving (see <see cref="FF_IOModes" />)</term><term>0x20</term></item>
		///				<item><term>Toggle output levels, when set will swap output logic levels</term><term>0x40</term></item>
		/// 		  </list> </summary>
		FF_SignalModes digIO1SignalMode;
		/// <summary> Digital IO 1 pulse width in milliseconds,<br />
		/// 		  Range 10 to 200 ms. </summary>
		unsigned int digIO1PulseWidth;
		/// <summary> I/O 2 Operating Mode
		/// 		  <list type=table>
		///				<item><term>Input Mode - FilterFlipper toggles when signalled (See <see cref="FF_SignalModes" />)</term><term>0x01</term></item>
		///				<item><term>Input Mode - FilterFlipper goes to position when signalled (See <see cref="FF_SignalModes" />)</term><term>0x02</term></item>
		///				<item><term>Output Mode - Output signal set to match position, where 2 = Hi, 1 = Lo</term><term>0x04</term></item>
		///				<item><term>Output Mode - Output signal high when FilterFlipper is moving</term><term>0x08</term></item>
		/// 		  </list> </summary>
		FF_IOModes digIO2OperMode;
		/// <summary> I/O 2 Signal Mode
		/// 		  <list type=table>
		///				<item><term>Signal is raised when Button Pressed i.e. Hi to Lo. Action taken is defined by <see cref="FF_IOModes" /></term><term>0x01</term></item>
		///				<item><term>Signal is raised on on rising edge Lo to Hi. Action taken is defined by <see cref="FF_IOModes" /></term><term>0x02</term></item>
		///				<item><term>Toggle Positions, when set will swap Position 1 and 2</term><term>0x04</term></item>
		///				<item><term>Output is set to either be hi when flipper at Position 2 or flipper is moving (see <see cref="FF_IOModes" />)</term><term>0x10</term></item>
		///				<item><term>Output is set to pulse when flipper operates, either when flipper reaches Position or flipper starts moving (see <see cref="FF_IOModes" />)</term><term>0x20</term></item>
		///				<item><term>Toggle output levels, when set will swap output logic levels</term><term>0x40</term></item>
		/// 		  </list> </summary>
		FF_SignalModes digIO2SignalMode;
		/// <summary> Digital IO 2 pulse width in milliseconds,<br />
		/// 		  Range 10 to 200 ms. </summary>
		unsigned int digIO2PulseWidth;
		/// <summary> Not used. </summary>
		int reserved1;
		/// <summary> Not used. </summary>
		unsigned int reserved2;
	} FF_IOSettings;

	#pragma pack()

    /// <summary> Build the DeviceList. </summary>
    /// <remarks> This function builds an internal collection of all devices found on the USB that are not currently open. <br />
    /// 		  NOTE, if a device is open, it will not appear in the list until the device has been closed. </remarks>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_BuildDeviceList(void);

	/// <summary> Gets the device list size. </summary>
	/// 		  \include CodeSnippet_identification.cpp
	/// <returns> Number of devices in device list. </returns>
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_GetDeviceListSize();

	/// <summary> Get the entire contents of the device list. </summary>
	/// <param name="stringsReceiver"> Outputs a SAFEARRAY of strings holding device serial numbers. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_GetDeviceList(SAFEARRAY** stringsReceiver);

	/// <summary> Get the contents of the device list which match the supplied typeID. </summary>
	/// <param name="stringsReceiver"> Outputs a SAFEARRAY of strings holding device serial numbers. </param>
	/// <param name="typeID">The typeID of devices to match, see \ref C_DEVICEID_page "Device serial numbers". </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID);

	/// <summary> Get the contents of the device list which match the supplied typeIDs. </summary>
	/// <param name="stringsReceiver"> Outputs a SAFEARRAY of strings holding device serial numbers. </param>
	/// <param name="typeIDs"> list of typeIDs of devices to be matched, see \ref C_DEVICEID_page "Device serial numbers"</param>
	/// <param name="length"> length of type list</param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	//short TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length);

	/// <summary> Get the entire contents of the device list. </summary>
	/// <param name="receiveBuffer"> a buffer in which to receive the list as a comma separated string. </param>
	/// <param name="sizeOfBuffer">	The size of the output string buffer. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer);

	/// <summary> Get the contents of the device list which match the supplied typeID. </summary>
	/// <param name="receiveBuffer"> a buffer in which to receive the list as a comma separated string. </param>
	/// <param name="sizeOfBuffer">	The size of the output string buffer. </param>
	/// <param name="typeID"> The typeID of devices to be matched, see \ref C_DEVICEID_page "Device serial numbers"</param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID);

	/// <summary> Get the contents of the device list which match the supplied typeIDs. </summary>
	/// <param name="receiveBuffer"> a buffer in which to receive the list as a comma separated string. </param>
	/// <param name="sizeOfBuffer">	The size of the output string buffer. </param>
	/// <param name="typeIDs"> list of typeIDs of devices to be matched, see \ref C_DEVICEID_page "Device serial numbers"</param>
	/// <param name="length"> length of type list</param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	short TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length);

	/// <summary> Get the device information from the USB port. </summary>
	/// <remarks> The Device Info is read from the USB port not from the device itself.<remarks>
	/// <param name="serialNo"> The serial number of the device. </param>
	/// <param name="info">    The <see cref="TLI_DeviceInfo"/> device information. </param>
	/// <returns> 1 if successful, 0 if not. </returns>
    /// 		  \include CodeSnippet_identification.cpp
	/// <seealso cref="TLI_GetDeviceListSize()" />
	/// <seealso cref="TLI_BuildDeviceList()" />
	/// <seealso cref="TLI_GetDeviceList(SAFEARRAY** stringsReceiver)" />
	/// <seealso cref="TLI_GetDeviceListByType(SAFEARRAY** stringsReceiver, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypes(SAFEARRAY** stringsReceiver, int * typeIDs, int length)" />
	/// <seealso cref="TLI_GetDeviceListExt(char *receiveBuffer, DWORD sizeOfBuffer)" />
	/// <seealso cref="TLI_GetDeviceListByTypeExt(char *receiveBuffer, DWORD sizeOfBuffer, int typeID)" />
	/// <seealso cref="TLI_GetDeviceListByTypesExt(char *receiveBuffer, DWORD sizeOfBuffer, int * typeIDs, int length)" />
	short TLI_GetDeviceInfo(char const * serialNo, TLI_DeviceInfo *info);

	/// <summary> Open the device for communications. </summary>
	/// <param name="serialNo">	The serial no of the device to be connected. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_connection1.cpp
	/// <seealso cref="FF_Close(char const * serialNo)" />
	short FF_Open(char const * serialNo);

	/// <summary> Disconnect and close the device. </summary>
	/// <param name="serialNo">	The serial no of the device to be disconnected. </param>
    /// 		  \include CodeSnippet_connection1.cpp
	/// <seealso cref="FF_Open(char const * serialNo)" />
	void FF_Close(char const * serialNo);

	/// <summary> Sends a command to the device to make it identify iteself. </summary>
	/// <param name="serialNo">	The device serial no. </param>
	void FF_Identify(char const * serialNo);

	/// <summary> Gets the hardware information from the device. </summary>
	/// <param name="serialNo">		    The device serial no. </param>
	/// <param name="modelNo">		    Address of a buffer to receive the model number string. Minimum 8 characters </param>
	/// <param name="sizeOfModelNo">	    The size of the model number buffer, minimum of 8 characters. </param>
	/// <param name="type">		    Address of a WORD to receive the hardware type number. </param>
	/// <param name="numChannels">	    Address of a short to receive the  number of channels. </param>
	/// <param name="notes">		    Address of a buffer to receive the notes describing the device. </param>
	/// <param name="sizeOfNotes">		    The size of the notes buffer, minimum of 48 characters. </param>
	/// <param name="firmwareVersion"> Address of a DWORD to receive the  firmware version number made up of 4 byte parts. </param>
	/// <param name="hardwareVersion"> Address of a WORD to receive the  hardware version number. </param>
	/// <param name="modificationState">	    Address of a WORD to receive the hardware modification state number. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
    /// 		  \include CodeSnippet_identify.cpp
	short FF_GetHardwareInfo(char const * serialNo, char * modelNo, DWORD sizeOfModelNo, WORD * type, WORD * numChannels, 
													   char * notes, DWORD sizeOfNotes, DWORD * firmwareVersion, WORD * hardwareVersion, WORD * modificationState);

	/// <summary> Gets version number of firmware. </summary>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The firmware version number made up of 4 byte parts. </returns>
    /// 		  \include CodeSnippet_identify.cpp
	DWORD FF_GetFirmwareVersion(char const * serialNo);

	/// <summary> Gets version number of the device software. </summary>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The device software version number made up of 4 byte parts. </returns>
    /// 		  \include CodeSnippet_identify.cpp
	DWORD FF_GetSoftwareVersion(char const * serialNo);

	/// <summary> Update device with stored settings. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <returns> <c>true</c> if successful, false if not. </returns>
    /// 		  \include CodeSnippet_connection1.cpp
	bool FF_LoadSettings(char const * serialNo);

	/// <summary> Persist the devices current settings. </summary>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> <c>true</c> if successful, false if not. </returns>
	bool FF_PersistSettings(char const * serialNo);

	/// <summary> Get number of positions. </summary>
	/// <remarks> The GetNumberPositions function will get the maximum position reachable by the device.<br />
	/// 		  The motor may need to be \ref C_MOTOR_sec10 "Homed" before this parameter can be used. </remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The number of positions. </returns>
	/// <seealso cref="FF_MoveToPosition(char const * serialNo, int index)" />
	/// <seealso cref="FF_GetPosition(char const * serialNo)" />
	/// <seealso cref="FF_Home(char const * serialNo)" />
    /// 		  \include CodeSnippet_move.cpp
	int FF_GetNumberPositions(char const * serialNo);

	/// <summary> Home the device. </summary>
	/// <remarks> Homing the device will set the device to a known state and determine the home position. </remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if move successfully started. </returns>
	/// <seealso cref="FF_GetNumberPositions(char const * serialNo)" />
	/// <seealso cref="FF_MoveToPosition(char const * serialNo, int index)" />
	/// <seealso cref="FF_GetPosition(char const * serialNo)" />
    /// 		  \include CodeSnippet_move.cpp
	short FF_Home(char const * serialNo);

	/// <summary> Move the device to the specified position (index). </summary>
	/// <remarks> The motor may need to be \ref C_MOTOR_sec10 "Homed" before a position can be set</remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <param name="position"> The required position. must be 1 or 2. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if move successfully started. </returns>
	/// <seealso cref="FF_GetNumberPositions(char const * serialNo)" />
	/// <seealso cref="FF_GetPosition(char const * serialNo)" />
	/// <seealso cref="FF_Home(char const * serialNo)" />
    /// 		  \include CodeSnippet_move.cpp
	short FF_MoveToPosition(char const * serialNo, FF_Positions position);

	/// <summary> Get the current position. </summary>
	/// <remarks> The current position is the last recorded position.<br />
	/// 		  The current position is updated either by the polling mechanism or<br />
	/// 		  by calling <see cref="RequestPosition" /> or <see cref="RequestStatus" />.</remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The current position 1 or 2. </returns>
	/// <seealso cref="FF_GetNumberPositions(char const * serialNo)" />
	/// <seealso cref="FF_MoveToPosition(char const * serialNo, int index)" />
	/// <seealso cref="FF_Home(char const * serialNo)" />
    /// 		  \include CodeSnippet_move.cpp
	int FF_GetPosition(char const * serialNo);

	/// <summary> Gets the I/O settings from filter flipper. </summary>
	/// <param name="serialNo">  The device serial no. </param>
	/// <param name="settings"> The address of the FF_IOSettings structure to receive the Filter Flipper I/O settings. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
	/// <seealso cref="FF_SetIOSettings(const char * serialNo, FF_IOSettings *settings)" />
	short FF_GetIOSettings(const char * serialNo, FF_IOSettings *settings);

	/// <summary> Sets the settings on filter flipper. </summary>
	/// <param name="serialNo">  The device serial no. </param>
	/// <param name="settings"> The address of the FF_IOSettings structure containing the new Filter Flipper I/O settings. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
	/// <seealso cref="FF_GetIOSettings(const char * serialNo, FF_IOSettings *settings)" />
	short FF_SetIOSettings(const char * serialNo, FF_IOSettings *settings);

	/// <summary> Gets the transit time. </summary>
	/// <returns> The transit time in milliseconds, range 300 to 2800 ms. </returns>
	/// <seealso cref="FF_SetTransitTime(const char * serialNo, unsigned int transitTime)" />
	unsigned int FF_GetTransitTime(const char * serialNo);

	/// <summary> Sets the transit time. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <param name="transitTime"> The transit time in milliseconds, range 300 to 2800 ms. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successful. </returns>
	/// <seealso cref="FF_GetTransitTime(const char * serialNo)" />
	short FF_SetTransitTime(const char * serialNo, unsigned int transitTime);

	/// <summary>	Request status bits. </summary>
	/// <remarks> This needs to be called to get the device to send it's current status.<br />
	/// 		  NOTE this is called automatically if Polling is enabled for the device using <see cref="FF_StartPolling(char const * serialNo, int milliseconds)" />. </remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successfully requested. </returns>
	/// <seealso cref="FF_GetStatusBits(char const * serialNo)" />
	/// <seealso cref="FF_StartPolling(char const * serialNo, int milliseconds)" />
	short FF_RequestStatus(char const * serialNo);

	/// <summary>Get the current status bits. </summary>
	/// <remarks> This returns the latest status bits received from the device.<br />
	/// 		  To get new status bits, use <see cref="FF_RequestStatus(char const * serialNo)" />
	/// 		  or use the polling functions, <see cref="FF_StartPolling(char const * serialNo, int milliseconds)" />.  </remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns>	The status bits from the device <list type=table>
	///				<item><term>0x00000001</term><term>CW hardware limit switch (0=No contact, 1=Contact).</term></item>
	///				<item><term>0x00000002</term><term>CCW hardware limit switch (0=No contact, 1=Contact).</term></item>
	///				<item><term>0x00000004</term><term>Not applicable.</term></item>
 	///				<item><term>0x00000008</term><term>Not applicable.</term></item>
	///				<item><term>0x00000010</term><term>Not applicable.</term></item>
 	///				<item><term>0x00000020</term><term>Not applicable.</term></item>
	///				<item><term>0x00000040</term><term>Shaft jogging clockwise (1=Moving, 0=Stationary).</term></item>
	///				<item><term>0x00000080</term><term>Shaft jogging counterclockwise (1=Moving, 0=Stationary).</term></item>
 	///				<item><term>0x00000100</term><term>Not applicable.</term></item>
	///				<item><term>0x00000200</term><term></term></item>
	///				<item><term>...</term><term></term></item>
	///				<item><term>0x00080000</term><term></term></item>
	///				<item><term>0x00100000</term><term>Digital input 1 state (1=Logic high, 0=Logic low).</term></item>
	///				<item><term>0x00200000</term><term>Digital input 2 state (1=Logic high, 0=Logic low).</term></item>
 	///				<item><term>0x00400000</term><term>Not applicable.</term></item>
	///				<item><term>0x00800000</term><term></term></item>
	///				<item><term>...</term><term></term></item>
	///				<item><term>0x02000000</term><term></term></item>
	///				<item><term>0x04000000</term><term>For Future Use.</term></item>
	///				<item><term>0x08000000</term><term>For Future Use.</term></item>
	///				<item><term>0x10000000</term><term>For Future Use.</term></item>
	///				<item><term>0x20000000</term><term>Active (1=Active, 0=Not active).</term></item>
	///				<item><term>0x40000000</term><term>For Future Use.</term></item>
	///				<item><term>0x80000000</term><term>Channel enabled (1=Enabled, 0=Disabled).</term></item>
	/// 		  </list> <remarks> Bits 21 and 22 (Digital Input States) are only applicable if the associated digital input is fitted to your controller - see the relevant handbook for more details. </remarks> </returns>
	/// <seealso cref="FF_RequestStatus(char const * serialNo)" />
	/// <seealso cref="FF_StartPolling(char const * serialNo, int milliseconds)" />
	DWORD FF_GetStatusBits(char const * serialNo);

	/// <summary> Starts the internal polling loop which continuously requests position and status. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <param name="milliseconds">The milliseconds polling rate. </param>
	/// <returns> <c>true</c> if successful, false if not. </returns>
	/// <seealso cref="FF_StopPolling(char const * serialNo)" />
	/// <seealso cref="FF_PollingDuration(char const * serialNo)" />
	/// <seealso cref="FF_RequestStatus(char const * serialNo)" />
	/// <seealso cref="FF_RequestPosition(char const * serialNo)" />
	/// \include CodeSnippet_connection1.cpp
	bool FF_StartPolling(char const * serialNo, int milliseconds);

	/// <summary> Gets the polling loop duration. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <returns> The time between polls in milliseconds or 0 if polling is not active. </returns>
	/// <seealso cref="FF_StartPolling(char const * serialNo, int milliseconds)" />
	/// <seealso cref="FF_StopPolling(char const * serialNo)" />
	/// \include CodeSnippet_connection1.cpp
	long FF_PollingDuration(char const * serialNo);

	/// <summary> Stops the internal polling loop. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <seealso cref="FF_StartPolling(char const * serialNo, int milliseconds)" />
	/// <seealso cref="FF_PollingDuration(char const * serialNo)" />
	/// \include CodeSnippet_connection1.cpp
	void FF_StopPolling(char const * serialNo);

	/// <summary> Requests that all settings are download from device. </summary>
	/// <remarks> This function requests that the device upload all it's settings to the DLL.</remarks>
	/// <param name="serialNo">	The device serial no. </param>
	/// <returns> The error code (see \ref C_DLL_ERRORCODES_page "Error Codes") or zero if successfully requested. </returns>
	short FF_RequestSettings(char const * serialNo);

	/// <summary> Clears the device message queue. </summary>
	/// <remarks> see \ref C_MESSAGES_page "Device Messages" for details on how to use messages. </remarks>
	/// <param name="serialNo"> The device serial no. </param>
	void FF_ClearMessageQueue(char const * serialNo);

	/// <summary> Registers a callback on the message queue. </summary>
	/// <remarks> see \ref C_MESSAGES_page "Device Messages" for details on how to use messages. </remarks>
	/// <param name="serialNo"> The device serial no. </param>
	/// <param name="functionPointer"> A function pointer to be called whenever messages are received. </param>
	/// <seealso cref="FF_MessageQueueSize(char const * serialNo)" />
	/// <seealso cref="FF_GetNextMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData)" />
	/// <seealso cref="FF_WaitForMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData)" />
	void FF_RegisterMessageCallback(char const * serialNo, void (* functionPointer)());

	/// <summary> Gets the MessageQueue size. </summary>
	/// <remarks> see \ref C_MESSAGES_page "Device Messages" for details on how to use messages. </remarks>
	/// <param name="serialNo"> The device serial no. </param>
	/// <returns> number of messages in the queue. </returns>
	/// <seealso cref="FF_RegisterMessageCallback(char const * serialNo, void (* functionPointer)())" />
	/// <seealso cref="FF_GetNextMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData)" />
	/// <seealso cref="FF_WaitForMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData)" />
	int FF_MessageQueueSize(char const * serialNo);

	/// <summary> Get the next MessageQueue item. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <param name="messageType"> The address of the parameter to receive the message Type. </param>
	/// <param name="messageID">   The address of the parameter to receive the message id. </param>
	/// <param name="messageData"> The address of the parameter to receive the message data. </param>
	/// <returns> <c>true</c> if successful, false if not. </returns>
	/// <seealso cref="FF_RegisterMessageCallback(char const * serialNo, void (* functionPointer)())" />
	/// <seealso cref="FF_MessageQueueSize(char const * serialNo)" />
	/// <seealso cref="FF_WaitForMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData)" />
	bool FF_GetNextMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData);

	/// <summary> Wait for next MessageQueue item. </summary>
	/// <param name="serialNo"> The device serial no. </param>
	/// <param name="messageType"> The address of the parameter to receive the message Type. </param>
	/// <param name="messageID">   The address of the parameter to receive the message id. </param>
	/// <param name="messageData"> The address of the parameter to receive the message data. </param>
	/// <returns> <c>true</c> if successful, false if not. </returns>
	/// <seealso cref="FF_RegisterMessageCallback(char const * serialNo, void (* functionPointer)())" />
	/// <seealso cref="FF_MessageQueueSize(char const * serialNo)" />
	/// <seealso cref="FF_GetNextMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData)" />
	bool FF_WaitForMessage(char const * serialNo, WORD * messageType, WORD * messageID, DWORD *messageData);

//}
/** @} */ // FilterFlipper
