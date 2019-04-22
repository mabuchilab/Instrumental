# -*- coding: utf-8 -*-
# Copyright 2019 Nate Bogdanowicz
import sys
from qtpy.QtWidgets import QApplication, QMainWindow, QFormLayout, QWidget, QLabel
from instrumental import Q_
from instrumental.drivers import Instrument, ManualFacet
from instrumental.gui import UDoubleSpinBox


class MyPowerSupply(Instrument):
    voltage = ManualFacet(type=float, units='volts')
    current = ManualFacet(type=float, units='amps')


if __name__ == '__main__':
    ps = MyPowerSupply()
    ps.observe('voltage', print)

    app = QApplication(sys.argv)
    win = QMainWindow()
    w = QWidget(win)
    win.setCentralWidget(w)
    fbox = QFormLayout()

    box1 = ps.facets.voltage.create_widget()
    fbox.addRow('Voltage', box1)
    box2 = ps.facets.current.create_widget()
    fbox.addRow('Current', box2)

    def set_box(event):
        box1.setUValue(event.new)
    ps.observe('voltage', set_box)

    def f():
        ps.voltage = '12 V'
    #box2.uValueChanged.connect(f)

    w.setLayout(fbox)
    win.show()
    app.exec_()
