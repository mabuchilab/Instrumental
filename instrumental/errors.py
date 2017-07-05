# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz


class Error(Exception):
    pass


class ConfigError(Error):
    pass


class TimeoutError(Error):
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
