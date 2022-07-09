"""
This is the impedance window
it checks impedances, of some openbci hardware
 References:
 https://eeghacker.blogspot.com/2014/04/impedance-of-electrodes-on-my-head.html
 https://openbci.com/community/openbci-measuring-electrode-impedance/

"""

import sys
import time
import csv
import random
import pdb

from PyQt5 import QtGui
from PyQt5.QtOpenGL import *
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPainter, QBrush, QPen, QPolygon
import numpy as np
import statistics as stats
from multiprocessing import Process, Queue

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes

SIMULATE = 0
FILE = 1
LIVESTREAM = 2

###########################################################


class impedance_win(QWidget):
    def __init__(
        self,
        hardware=None,
        model=None,
        sim_type=None,
        data_type=None,
        serial_port=None,
        parent=None,
        board_id=None,
    ):
        super().__init__()

        self.parent = parent
        self.sim_type = sim_type
        self.hardware = hardware
        self.model = model
        self.serial_port = serial_port

        self.col_thresh = [50, 100, 250, 500, 1000]
        self.col = [
            QtCore.Qt.green,
            QtCore.Qt.yellow,
            QtCore.Qt.darkYellow,
            QtCore.Qt.red,
            QtCore.Qt.black,
        ]

        self.electrodes = [
            "F7",
            "F3",
            "F4",
            "F8",
            "C3",
            "C4",
            "P7",
            "P3",
            "P4",
            "P8",
            "O1",
            "O2",
            "T7",
            "T8",
            "Fp1",
            "Fp2",
        ]
        self.chans_ind = "12345678qwertyui"
        self.chan_num = 16

        self.coords = {
            "F7": [-0.06734486, 0.04071033, -0.01094572],
            "F3": [-0.04815716, 0.05090548, 0.04043975],
            "F4": [0.04968343, 0.0520495, 0.03911898],
            "F8": [0.0700096, 0.04257685, -0.01150164],
            "C3": [-0.06264376, -0.01114863, 0.06168519],
            "C4": [0.06433047, -0.01044761, 0.0609395],
            "P7": [-0.06942608, -0.07040219, -0.00238371],
            "P3": [-0.05080589, -0.07551572, 0.05361679],
            "P4": [0.05335484, -0.07529757, 0.054212],
            "P8": [0.07002167, -0.07003375, -0.00243451],
            "O1": [-0.02819185, -0.10777896, 0.00847191],
            "O2": [0.02860323, -0.10749813, 0.00843453],
            "T7": [-0.06942608, -0.07040219, -0.00238371],
            "T8": [0.07002167, -0.07003375, -0.00243451],
            "Fp1": [-0.02821418, 0.080432, -0.0066997],
            "Fp2": [0.02863169, 0.08137015, -0.00678597],
        }

        ### need a tertiary window to select which channels
        # a drop down for each channel - which deselects from a given if current selected
        # number of channel options is based on the model

        self.params = BrainFlowInputParams()
        self.params.serial_port = serial_port

        # set board id based on parameters only if it wasn't given to us
        print('impedncae wuin\'s board id  {}'.format(board_id))
        if board_id == None:
            if self.data_type == "Task live":
                if self.hardware == "openBCI":
                    if self.model == "Ganglion":
                        self.board_id = 1
                    elif self.model == "Cyton":
                        self.board_id = 0
                    elif self.model == "Cyton-Daisy":
                        self.board_id = 2
                elif self.hardware == "Muse":
                    if self.model == "Muse 2":
                        self.board_id = 22
                    elif self.model == "Muse S":
                        self.board_id = 21
            elif self.data_type == "Task simulate":
                self.board_id = -1
        else:
            self.board_id = board_id

        # Brainflow Initialization

        # BoardShim.enable_dev_board_logger()

        # MANUALLY SPECIFY COM PORT IF USING CYTON OR CYTON DAISY
        # if not specified, will use first available port
        # should be a string representing the COM port that the Cyton Dongle is connected to.
        # e.g for Windows users 'COM3', for MacOS or Linux users '/dev/ttyUSB1

        self.setMinimumSize(800, 800)
        self.setWindowIcon(QtGui.QIcon("utils/logo_icon.jpg"))

        # setting window title
        self.setWindowTitle("Impedance Window")

        # init layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.title_layout = QHBoxLayout()

        self.title = QLabel()
        self.title.setFont(QtGui.QFont("Arial", 14))
        self.title.setText("Impedances")
        # self.title_layout.addWidget(self.title)

        self.layout.setContentsMargins(100, 100, 100, 100)
        self.title_layout.setContentsMargins(50, 50, 50, 50)

        self.layout.addLayout(self.title_layout, 0, 0, 1, -1, QtCore.Qt.AlignHCenter)

        self.setLayout(self.layout)
        # self.layout.setContentsMargins(100,100,100,100)

        self.data = []
        self.running_test = False
        self.display_instructions()

        self.run = True

        self.color = QtCore.Qt.blue

        self.loop_timer = QTimer()
        # making it a precision timer
        self.loop_timer.setTimerType(0)
        self.loop_timer.setSingleShot(True)
        # setting the function to call when it times out
        # IMPORTANT: to change the function it calls, must first use timer.disconnect() to remove the previous one
        # otherwise will call both new and old fucntions
        self.loop_timer.timeout.connect(self.start_iteration)

        self.loop_running = False

        # To ensure we dont try to close the object a second time
        self.finished = False

        self.init_hardware()

    def init_hardware(self):

        # let's start eeg receiving!
        # self.start_data_stream()

        self.board = BoardShim(self.board_id, self.params)
        self.board.prepare_session()
        self.chan_ind = self.board.get_exg_channels(self.board_id)
        self.chan_num = len(self.chan_ind)
        print(
            "init hardware is running with hardware", self.hardware, "model", self.model
        )

        self.hardware_connected = True

        if self.board_id == 2:
            # this is eden's cyton daisy stuff
            # Think Pulse
            self.board.config_board(
                "x1040010Xx2040010Xx3040010Xx4040010Xx5040010Xx6040010Xx7040010Xx8040010XxQ040010XxW040010XxE040010XxR040010XxT040010XxY040010XxU040010XxI040010X"
            )
            # Reinitialize the 15/16 channel for EOG
            # board.config_board("xU060100XxI060100X")

            res = self.board.config_board(
                "z110Zz210Zz310Zz410Zz510Zz610Zz710Zz810Zzq10Zzw10Zze10Zzr10Zzt10Zzy10Zzu10Zzi10Z"
            )
            print(res)

            self.board.start_stream(45000, None)
            self.impedances = [0] * self.chan_num

        elif self.board_id == 1:
            # ganglion impedances based on
            # https://github.com/OpenBCI/brainflow/blob/master/tests/python/ganglion_resist.py
            # expected result: 5 seconds of resistance data(unknown sampling rate) after that 5 seconds of exg data
            self.board.config_board("z")
            print('sent board z, not yet start stream')
            self.board.start_stream(45000, None)
            time.sleep(5)
            print('abbout to send board Z')
            self.board.config_board("Z")
            time.sleep(5)
            data = self.board.get_board_data()

            # self.board.stop_stream ()
            # self.board.release_session ()

            print (data)

            resistance_channels = BoardShim.get_resistance_channels (BoardIds.GANGLION_BOARD.value)
            print (resistance_channels)

    def closeEvent(self, event):
        # this code will autorun just before the window closes
        # we will check whether streams are running, if they are we will close them
        print("close event works")
        self.on_end()


    def loop_start(self):
        print("starting loop")
        self.loop_running = True
        self.loop_timer.timeout.disconnect()
        self.loop_timer.timeout.connect(self.start_iteration)
        self.loop_timer.start(1000)
        self.update()

    # def loop_end(self):
    #     print("ending loop")
    #     self.loop_running = False
    #     self.update()
    #     self.loop_timer.timeout.disconnect()
    #     self.loop_timer.timeout.connect(self.start_iteration)
    #     self.loop_timer.start(1000)

    def start_iteration(self):
        # called by hitting enter
        if not self.finished:
            time.sleep(1)
            self.data = (
                self.board.get_board_data()
            )  # will need to be a consist number of samples
            self.impedances = list(range(self.chan_num))
            for i in range(self.chan_num):
                # average with the prevous x number of fft data
                # but this isn't fft - so wtf
                self.filter_custom(i)
                # print(len(self.data[i,:]))
                # current is toggling on and off at 31.5 hz (maybe)
                # so observed voltage should be a sine wave. ideally, we would find its amplitude but I'm lazy
                # use stdev as proxy.
                chan_std_uV = stats.stdev(self.data[i,:])
                self.impedances[i] = ((stats.sqrt( 2.0 ) * (chan_std_uV) * 1.0e-6) / 6.0e-9 - 2200)/1000
            print(self.impedances)
            """
            HERE
            """
            # need to do some smoothing from the past 6 seconds to take out instantaneous
            self.loop_start()
        else:
            print("exiting")
            time.sleep(2)
            self.on_end()

    def filter_custom(self, chan):
        DataFilter.perform_highpass(
            self.data[chan],
            BoardShim.get_sampling_rate(self.board_id),
            1.0,
            4,
            FilterTypes.BUTTERWORTH.value,
            0,
        )
        DataFilter.perform_bandstop(
            self.data[chan],
            BoardShim.get_sampling_rate(self.board_id),
            60.0,
            1.0,
            3,
            FilterTypes.BUTTERWORTH.value,
            0,
        )

    def display_instructions(self):
        # this will run at the beginning and needs a button press before anything else will happen
        self.label = QLabel()
        self.label.setFont(QtGui.QFont("Arial", 14))
        self.label.setText(
            "Press enter once you have finished positioning the headset "
        )
        self.layout.addWidget(self.label)

    def keyPressEvent(self, event):
        if event.key() == Qt.Qt.Key_Space:
            print("received user input")
        elif event.key() == Qt.Qt.Key_Return or event.key == Qt.Qt.Key_Enter:
            if self.hardware_connected and not self.running_test:
                self.running_test = True
                self.label.setVisible(False)
                self.start_iteration()

    def paintEvent(self, event):
        # here is where we draw stuff on the screen
        # you give drawing instructions in pixels - here I'm getting pixel values based on window size
        print("paint event runs")
        painter = QPainter(self)
        if self.loop_running:
            radius = self.geometry().width() // 18
            center = self.geometry().width() // 2
            for i in range(self.chan_num):
                print(i)
                temp_coords = self.coords[self.electrodes[i]]
                x = temp_coords[0] * 2500
                y = temp_coords[1] * 2500
                temp_col = 0
                col_found = False
                for col in range(len(self.col_thresh)):
                    print(self.impedances[i])
                    # print(self.col_thresh[col])
                    print(
                        "Is impedance at electrode {} ({}) lower than threshhold ({}): {}".format(
                            self.electrodes[i],
                            self.impedances[i],
                            self.col_thresh[col],
                            self.impedances[i] < self.col_thresh[col],
                        )
                    )
                    print("debug1: {}".format(col_found))
                    if col_found == False:
                        print("debug2")
                        if self.impedances[i] < self.col_thresh[col]:
                            print("debug3")
                            temp_col = self.col[col]
                            print(
                                "therefor the colour of should be {}".format(
                                    self.col[col]
                                )
                            )
                            col_found = True
                            # print("found colour")
                            # print(self.col_thresh[col])
                            # print(temp_col)
                if col_found == False:
                    temp_col = self.col[-1]
                painter.setBrush(
                    QBrush(temp_col, QtCore.Qt.SolidPattern)
                )  # QtCore.Qt.SolidPattern
                painter.drawEllipse(center + x, center + y, radius, radius)
                painter.drawText(
                    center + x - 30,
                    center + y,
                    self.electrodes[i] + ": " + str(self.impedances[i]),
                )
        elif self.finished:
            # no need to paint anything specifically
            pass

    def on_end(self):
        self.board.stop_stream()
        self.board.release_session()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = impedance_win()
    win.show()
    sys.exit(app.exec())
