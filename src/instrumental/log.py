# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz

import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET


#DEFAULT_FMT = "[%(levelname)8s:%(threadName)s]%(asctime)s %(name)s: %(message)s"
DEFAULT_FMT = "[%(levelname)8s]%(asctime)s %(name)s: %(message)s"


def get_logger(name='', add_NullHandler=False):
    logger = logging.getLogger(name)
    if add_NullHandler:
        logger.addHandler(logging.NullHandler())
    return logger


class Filter(object):
    def __init__(self, levels):
        self.cache = {}
        self.lone_levels = {}
        self.levels = dict(levels)
        for name in list(levels.keys()):
            if name.endswith('$'):
                self.lone_levels[name[:-1]] = self.levels.pop(name)

    def _get_level(self, name):
        try:
            return self.lone_levels[name]
        except KeyError:
            pass

        try:
            return self.cache[name]
        except KeyError:
            pass

        base_name = name
        while True:
            try:
                level = self.levels[base_name]
                self.cache[name] = level
                return level
            except KeyError:
                pass

            if not base_name:
                break
            elif '.' in base_name:
                base_name = base_name.rsplit('.', 1)[0]
            else:
                base_name = ''

        return WARNING  # Default

    def filter(self, record):
        level = self._get_level(record.name)
        display = record.levelno >= level
        return display


PKG_LOGGER = get_logger('instrumental')
ROOT_LOGGER = get_logger(add_NullHandler=True)


def log_to_screen(level=INFO, fmt=None):
    fmt = fmt or DEFAULT_FMT
    handler = logging.StreamHandler()
    handler.setLevel(DEBUG)

    if isinstance(level, dict):
        min_level = min(l for l in level.values())
    else:
        min_level = level
        level = {'': level}
    handler.addFilter(Filter(level))

    handler.setFormatter(logging.Formatter(fmt=fmt))
    ROOT_LOGGER.addHandler(handler)
    if ROOT_LOGGER.getEffectiveLevel() > min_level:
        ROOT_LOGGER.setLevel(min_level)
    return ROOT_LOGGER


def log_to_file(filename, level=INFO, fmt=None, mode='a'):
    fmt = fmt or DEFAULT_FMT
    handler = logging.FileHandler(filename, mode=mode)
    handler.setLevel(DEBUG)

    if isinstance(level, dict):
        min_level = min(l for l in level.values())
    else:
        min_level = level
        level = {'': level}
    handler.addFilter(Filter(level))

    handler.setFormatter(logging.Formatter(fmt=fmt))
    ROOT_LOGGER.addHandler(handler)
    if ROOT_LOGGER.getEffectiveLevel() > min_level:
        ROOT_LOGGER.setLevel(min_level)
    return ROOT_LOGGER
