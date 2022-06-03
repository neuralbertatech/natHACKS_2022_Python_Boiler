import sys
import time
import serial
import pygatt
from binascii import hexlify
import asyncio

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPainter, QBrush, QPen, QPolygon
import numpy as np


class ard_wind_on(QWidget):
    def __init__(self, parent=None, arduino_port=None, arduino_con=None):
        super().__init__()
        self.parent = parent
        self.arduino_port = arduino_port
        self.arduino_con = arduino_con

        self.stim_ampl = 5
        self.stim_freq = 10
        self.stim_dur = 10

        ####################################
        ##### Init Main Window Globals #####
        ####################################

        """
        |------------------INPUTS-------------------|    
        |                                           |
        |                   AMPL                    |
        |                   FREQ                    |
        |                   DUR                     |
        |                                           |
        |------------------ACTIONS------------------|
        |                                           |
        |                   START                   |
        |                                           |
        |-------------------------------------------|

        """

        self.setMinimumSize(600, 600)
        self.setWindowIcon(QtGui.QIcon("utils/logo_icon.jpg"))

        # setting window title
        self.setWindowTitle("Arduino Testing Window")

        # init layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(100, 100, 100, 100)

        self.header_layout = QVBoxLayout()
        self.info = QLabel()
        self.info.setFont(QtGui.QFont("Arial", 14))
        self.info.setText(
            "The following serial port has been selected: {}".format(
                str(self.arduino_port)
            )
        )
        self.header_layout.addWidget(self.info)
        self.layout.addLayout(self.header_layout, 1, 0)

        ###################################
        ##### Init GUI Input Elements #####
        ###################################

        ### INIT INPUT LAYOUTS ###
        # Create layouts explicitly for all GUI input fields

        """
        |------------------INPUTS-------------------|    
        |                                           |
        |                   AMPL                    |
        |                   FREQ                    |
        |                   DUR                     |
        |                                           |
        |-------------------------------------------|


        """
        self.amplitude_layout = QVBoxLayout()
        self.frequency_layout = QVBoxLayout()
        self.duration_layout = QVBoxLayout()

        # set up dropdown for amplitude
        self.amplitude_label = QLabel("Amplitude  (mA)")
        self.amplitude_dropdown = QComboBox()
        self.amplitude_dropdown.setPlaceholderText("Select pulse train strength")
        self.amplitude_dropdown.addItems(["1", "2", "4", "8", "16"])
        self.amplitude_dropdown.activated.connect(self.handle_amplitude_choice)
        self.amplitude_layout.addWidget(self.amplitude_label)
        self.amplitude_layout.addWidget(self.amplitude_dropdown)

        # set up dropdown for frequency
        self.frequency_label = QLabel("frequency (Hz)")
        self.frequency_dropdown = QComboBox()
        self.frequency_dropdown.setPlaceholderText("Select pulse train wavelength")
        self.frequency_dropdown.addItems(["4", "6", "8", "10", "12", "14", "16", "18"])
        self.frequency_dropdown.activated.connect(self.handle_frequency_choice)
        self.frequency_dropdown.setEnabled(False)  # starts disabled
        self.frequency_layout.addWidget(self.frequency_label)
        self.frequency_layout.addWidget(self.frequency_dropdown)

        # set up dropdown for duration
        self.duration_label = QLabel("duration (s)")
        self.duration_dropdown = QComboBox()
        self.duration_dropdown.setPlaceholderText("Select pulse train duration")
        self.duration_dropdown.addItems(["5", "10", "15", "20", "25", "30"])
        self.duration_dropdown.activated.connect(self.handle_duration_choice)
        self.duration_dropdown.setEnabled(False)  # starts disabled
        self.duration_layout.addWidget(self.duration_label)
        self.duration_layout.addWidget(self.duration_dropdown)

        self.amplitude_layout.setContentsMargins(100, 50, 100, 15)
        self.frequency_layout.setContentsMargins(100, 15, 100, 15)
        self.duration_layout.setContentsMargins(100, 15, 100, 50)
        self.layout.addLayout(self.amplitude_layout, 2, 0)
        self.layout.addLayout(self.frequency_layout, 3, 0)
        self.layout.addLayout(self.duration_layout, 4, 0)

        ####################################
        ##### Init GUI Action Elements #####
        ####################################

        """

        |------------------ACTIONS------------------|
        |                                           |
        |                   START                   |
        |                                           |
        |-------------------------------------------|

        """

        # set up a button to activate / deactivate the arduino
        self.arduino_button = QPushButton("Activate Arduino")
        self.arduino_button.setEnabled(False)
        self.layout.addWidget(self.arduino_button, 6, 0, 1, -1, QtCore.Qt.AlignHCenter)
        self.arduino_button.clicked.connect(self.activate_arduino)

        self.TDCS = False

        ### Conditional Connection Initialization
        if self.arduino_con == "Wireless":
            self.TDCS_UUID = "00001101-0000-1000-8000-00805f9b34fb"
            self.on_value = bytearray([0x01])
            self.off_value = bytearray([0x00])
            print("Arduino Nano BLE LED Peripheral Central Service")
            print("Looking for Arduino Nano 33 BLE Sense Peripheral Device...")
            self.arduino = pygatt.BGAPIBackend(
                serial_port=self.arduino_port
            )  # virtual COM port for the BlueGiga dongle
            try:
                self.arduino.start()
                device = self.arduino.connect(
                    "C8:87:39:14:AC:BF"
                )  # MAC address of the Arduino
                print(device)
            except (pygatt.exceptions.NotConnectedError):
                print("Could not find Arduino Nano 33 BLE Sense Peripheral")
        elif self.arduino_con == "Wired":
            self.arduino = serial.Serial(
                port=self.arduino_port, baudrate=9600, timeout=0.1
            )
        elif self.arduino_con == "NeuroStimDuino":
            self.arduino = serial.Serial(
                port=self.arduino_port, baudrate=115200, timeout=0.1
            )
        elif self.arduino_con == "Debug":
            pass

    #########################################
    ##### Functions for Handling Inputs #####
    #########################################

    def handle_amplitude_choice(self):
        self.stim_ampl = self.amplitude_dropdown.currentText()
        self.frequency_dropdown.setEnabled(True)

    def handle_frequency_choice(self):
        self.stim_freq = self.frequency_dropdown.currentText()
        self.duration_dropdown.setEnabled(True)

    def handle_duration_choice(self):
        self.stim_dur = self.duration_dropdown.currentText()
        self.arduino_button.setEnabled(True)

    def activate_arduino(self):
        if self.arduino_con == "Wireless":
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(self.run())
            except KeyboardInterrupt:
                print("\nReceived Keyboard Interrupt")
            finally:
                print("Program finished")
        elif self.arduino_con == "Wired":
            if self.arduino_button.text() == "Activate Arduino":
                self.arduino.write(b"0")
                self.arduino_button.setText("Deactivate Arduino")
            else:
                self.arduino.write(b"1")
                self.arduino_button.setText("Activate Arduino")
        elif self.arduino_con == "NeuroStimDuino":
            wait = 2
            channel = 1

            def read(arduino):
                try:
                    msg = arduino.read(
                        arduino.inWaiting()
                    ).decode()  # read everything in the input buffer
                    print(msg)
                    return msg
                except:
                    pass

            time.sleep(wait)  # wait for arduino init on serial connection
            read(self.arduino)  # get initial starting message

            cmd_string = ("RSET 1" + "\r\n").encode(
                "ascii"
            )  # create encoded string to set amplitude of channel 1
            self.arduino.write(cmd_string)  # write

            time.sleep(wait)  # wait for arduino init on serial connection
            read(self.arduino)  # get initial starting message

            cmd_string = ("AMPL 1 {}".format(self.stim_ampl) + "\r\n").encode(
                "ascii"
            )  # create encoded string to set amplitude of channel 1
            self.arduino.write(cmd_string)  # write
            time.sleep(wait)
            read(self.arduino)  # confirm amp set correctly

            cmd_string = ("FREQ 1 {}".format(self.stim_freq) + "\r\n").encode(
                "ascii"
            )  # create encoded string to set amplitude of channel 1
            self.arduino.write(cmd_string)  # write
            time.sleep(wait)
            read(self.arduino)  # confirm amp set correctly

            cmd_string = (
                "STIM {} {} 0".format(channel, self.stim_dur) + "\r\n"
            ).encode("ascii")
            self.arduino.write(cmd_string)  # write
            time.sleep(wait)
            read(self.arduino)  # confirm amp set correctly

        elif self.arduino_con == "Debug":
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ard_wind_on()
    win.show()
    sys.exit(app.exec())
