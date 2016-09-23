# -*- coding: utf-8 -*-
# Copyright 2016 Nate Bogdanowicz
import sys

__all__ = ['QtCore', 'QtGui']
QtCore, QtGui = None, None
HAS_QT, PYSIDE, PYQT = False, False, False


def load_PyQt4():
    global QtCore, QtGui, HAS_QT, PYQT
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    from PyQt4 import QtCore, QtGui
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot
    sys.modules[__name__ + '.QtCore'] = QtCore
    sys.modules[__name__ + '.QtGui'] = QtGui
    PYQT = True
    HAS_QT = True


def load_PySide():
    global QtCore, QtGui, HAS_QT, PYSIDE
    from PySide import QtCore, QtGui
    sys.modules[__name__ + '.QtCore'] = QtCore
    sys.modules[__name__ + '.QtGui'] = QtGui
    PYSIDE = True
    HAS_QT = True


if 'PyQt4' in sys.modules:
    load_PyQt4()
elif 'PySide' in sys.modules:
    load_PySide()
else:
    try:
        load_PyQt4()
    except ImportError:
        try:
            load_PySide()
        except ImportError:
            pass
