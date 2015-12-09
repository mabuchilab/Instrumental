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
