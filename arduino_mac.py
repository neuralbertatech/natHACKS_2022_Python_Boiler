"""
This is the oddball task
- it displays either a blue or green circle and records when user hits space
it pumps data about what happens when to an lsl stream
it also receive eeg data from a muse, or simulates it
This data is recorder along with events
EVENT KEY:
0 - Begin trial
1 - normal color displayed (blue)
2 - oddball color displayed (green)
3 - user pressed space
11 - end trial
It contains partially complete code to graph ERP afterwards.
The data is stored with tines normalized (timestamp 0 when stim first displayed, for each trial)
so setting up an ERP graph should be reasonably simple
Project ideas: any project where the user sees something displayed and interacts with it, while eeg is recorded
"""

import sys
import time
import csv
import random
import os

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPainter, QBrush, QPen, QPolygon
import numpy as np

import logging
import asyncio
import platform
import ast

# use bleak version 0.1.12 for mac

# import CoreBluetooth
from bleak import BleakClient
from bleak import BleakScanner
from bleak import discover


class ard_mac_on(QWidget):
    def __init__(self, parent=None, arduino_port=None):
        super().__init__()

        self.parent = parent
        self.arduino_port = arduino_port

        self.setMinimumSize(600, 600)
        self.setWindowIcon(QtGui.QIcon("utils/logo_icon.jpg"))

        # setting window title
        self.setWindowTitle("Arduino Testing Window")

        # init layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(100, 100, 100, 100)
        self.label = QLabel()
        self.label.setFont(QtGui.QFont("Arial", 14))
        self.label.setText(
            "This is a placeholder window to test the arduino function and turn it on and off"
        )
        self.layout.addWidget(self.label)
        self.info = QLabel()
        self.info.setFont(QtGui.QFont("Arial", 14))
        self.info.setText(
            "The following serial port has been selected: " + str(self.arduino_port)
        )
        self.layout.addWidget(self.info)

        # set up a button to activate / deactivate the arduino
        self.arduino_button = QPushButton("Activate Arduino")
        self.arduino_button.setEnabled(True)
        self.layout.addWidget(self.arduino_button, 4, 0, 1, -1, QtCore.Qt.AlignHCenter)
        self.arduino_button.clicked.connect(self.activate_arduino)

        # This values was randomly generated - it must match between the Central and Peripheral devices
        # Any changes you make here must be suitably made in the Arduino program as well
        self.TDCS_UUID = "00001101-0000-1000-8000-00805f9b34fb"

        self.on_value = bytearray([0x01])
        self.off_value = bytearray([0x00])

        self.TDCS = False

    def activate_arduino(self):
        if self.arduino_button.text() == "Activate Arduino":
            self.arduino_button.setText("Deactivate Arduino")
        else:
            self.arduino_button.setText("Activate Arduino")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ard_turn_on()
    win.show()
    sys.exit(app.exec())
