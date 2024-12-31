# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz


class Error(Exception):
    pass


class ConfigError(Error):
    pass


class TimeoutError(Error):
    pass


class UnsupportedFeatureError(Error):
    pass


class InstrumentTypeError(Error):
    pass


class InstrumentNotFoundError(Error):
    pass


class InstrumentExistsError(Error):
    pass


class LibError(Error):
    MESSAGES = {}
    MSG_FORMAT = '({:d}) {}'
    def __init__(self, code=None, msg=''):
        self.code = code
        if code is not None:
            if not msg:
                msg = self.MESSAGES.get(code)
            msg = self.MSG_FORMAT.format(code, msg)
        super(LibError, self).__init__(msg)


class PCOError(Exception):
    def __init__(self, return_code):
        error_text = self.get_error_text(return_code)

        # Call the base class constructor with the parameters it needs
        super().__init__(error_text)

        self.return_code = return_code

    @staticmethod
    def return_code_to_hex_string(return_code):
        """Write the return code integer as a hex string

        This is the inverse of PCOError.return_code_to_hex_string()
        """
        return_code_bytes = return_code.to_bytes(
            4, byteorder="big", signed=True)
        return_code_hex_string = return_code_bytes.hex().upper()
        return_code_hex_string = "0x" + return_code_hex_string
        return return_code_hex_string

    @staticmethod
    def hex_string_to_return_code(hex_string):
        """Convert a hex string into the corresponding return code integer

        This is the inverse of PCOError.return_code_to_hex_string(). The string
        provided should only contain the characters 0-9 and A-F.

        Example: PCOError.hex_string_to_return_code("0xF00000FF")
        """
        # Strip leading "0x" if present
        if hex_string[0:2] == "0x":
            hex_string = hex_string[2:]

        return_code_bytes = bytes.fromhex(hex_string)
        return_code = int.from_bytes(
            return_code_bytes, byteorder="big", signed=True)

        return return_code

    @classmethod
    def get_error_text(cls, return_code):
        """Turn a pco.sdk error code into a useful/informative string
        
        Use C function for this purpose if possible. Only works if that C code
        is compiled, which may be done automatically during installation, or may
        need to be done manually. Otherwise it will raise a ModuleNotFoundError.
        See issue 30 on instrumental's github:
        https://github.com/mabuchilab/Instrumental/issues/30

        If the compiled function doesn't work, this function will convert the
        error code to a hex string and refer the user to the PCO_errt.h from the
        PCO SDK to interpret the error manually. Additional info about the
        formatting of error codes is available in PCO_err.h (note the missing
        "t" in this file name compared to the other one).
        """
        try:
            # Use instrumental's nice wrapper of PCO_GetErrorText()
            import instrumental.drivers.cameras.pco
            return instrumental.drivers.cameras.pco.get_error_text(return_code)
        except ImportError:
            # If the wrapper doesn't work, we'll just print out the error code
            # as a hex string
            return_code_hex = cls.return_code_to_hex_string(return_code)
            if return_code_hex[0:3] == "0xA":
                # "Common errors" start with 0xA and have more bits masked in
                # PCO_errt.h. In this case we need to mask all but first 4
                # bits and last 8 bits.
                mask = cls.hex_string_to_return_code("0xF00000FF")
            else:
                # For other errors fewer bits are masked
                mask = cls.hex_string_to_return_code("0xF000FFFF")

            # This masked code should appear in PCO_errt.h in a comment next to
            # the error string
            masked_return_code = return_code & mask
            masked_return_code_hex = cls.return_code_to_hex_string(
                masked_return_code)

            error_text = ("PCO Error code: " + return_code_hex + ", "
                          "Look for " + masked_return_code_hex + " in "
                          "PCO_errt.h")

            return error_text
